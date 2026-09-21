"""
Server Connection Management
"""

import asyncio
import re
import time
import uuid
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field

from tunnel.utils.logging import setup_logger

logger = setup_logger("tunnel.connection")


RESERVED_SUBDOMAINS = {
    "www", "api", "dashboard", "metrics", "health",
    "webhooks", "webhook", "admin", "static", "assets",
    "tunnel", "mail", "ftp", "localhost",
}

_SUBDOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def validate_subdomain(subdomain: Optional[str]) -> Tuple[bool, str]:
    """Validate requested subdomain. Returns (ok, reason)."""
    if not subdomain:
        return True, ""  # auto-generated, always ok
    s = subdomain.lower()
    if s in RESERVED_SUBDOMAINS:
        return False, f"Subdomain '{subdomain}' is reserved"
    if not _SUBDOMAIN_RE.match(s):
        return False, f"Invalid subdomain '{subdomain}': use 1-63 chars a-z 0-9 hyphen"
    return True, ""


@dataclass
class Tunnel:
    """Represents an active tunnel connection"""
    tunnel_id: str
    subdomain: str
    websocket: Any  # WebSocket object
    local_port: int
    created_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)
    is_active: bool = True
    pending_requests: Dict[str, asyncio.Future] = field(default_factory=dict)
    tcp_enabled: bool = False
    tcp_public_port: Optional[int] = None
    tcp_target_host: str = "127.0.0.1"
    tcp_target_port: Optional[int] = None
    
    def touch(self):
        """Update last activity timestamp"""
        self.last_ping = time.time()
    
    def add_request(self, request_id: str, future: asyncio.Future):
        """Add pending request"""
        self.pending_requests[request_id] = future
        self.touch()
    
    def complete_request(self, request_id: str, response: Any):
        """Complete a pending request"""
        if request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_result(response)
        self.touch()
    
    def close(self):
        """Close tunnel and cleanup"""
        self.is_active = False
        for future in self.pending_requests.values():
            if not future.done():
                future.set_exception(Exception("Tunnel closed"))
        self.pending_requests.clear()


class ConnectionManager:
    """Manages all tunnel connections"""
    
    def __init__(self, base_domain: str = "tunnel.dev", use_https: bool = False):
        self.base_domain = base_domain
        self.use_https = use_https
        self.tunnels: Dict[str, Tunnel] = {}  # tunnel_id -> Tunnel
        self.subdomain_map: Dict[str, str] = {}  # subdomain -> tunnel_id
        # Lazy lock: asyncio.Lock() binds to the running loop on py3.8/3.9,
        # so creating it in __init__ breaks when no loop runs (tests, import).
        self._lock: Optional[asyncio.Lock] = None
        self._request_counter = 0

    def _get_lock(self) -> asyncio.Lock:
        """Return lock, creating it inside the running loop on first use"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    def _generate_id(self) -> str:
        """Generate unique tunnel ID"""
        return f"tun_{uuid.uuid4().hex[:12]}"
    
    def _generate_subdomain(self) -> str:
        """Generate unique subdomain"""
        return uuid.uuid4().hex[:8]
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        self._request_counter += 1
        return f"req_{self._request_counter}_{int(time.time() * 1000)}"
    
    def set_base_domain(self, domain: str):
        """Update base domain (e.g. from CLI --domain or TUNNEL_DOMAIN env)"""
        if domain:
            self.base_domain = domain

    def set_use_https(self, enabled: bool):
        """Update URL scheme flag"""
        self.use_https = bool(enabled)

    def get_public_url(self, subdomain: str, use_https: Optional[bool] = None) -> str:
        """Get public URL for subdomain"""
        https = self.use_https if use_https is None else use_https
        scheme = "https" if https else "http"
        return f"{scheme}://{subdomain}.{self.base_domain}"
    
    async def create_tunnel(self, websocket: Any, local_port: int,
                           requested_subdomain: Optional[str] = None,
                           tcp_enabled: bool = False,
                           tcp_public_port: int = 0,
                           tcp_target_host: str = "127.0.0.1",
                           tcp_target_port: Optional[int] = None) -> Optional[Tunnel]:
        """Create new tunnel"""
        async with self._get_lock():
            # Generate or validate subdomain
            if requested_subdomain:
                ok, _ = validate_subdomain(requested_subdomain)
                if not ok:
                    return None  # reserved / invalid
                lowered = requested_subdomain.lower()
                if lowered in self.subdomain_map or requested_subdomain in self.subdomain_map:
                    return None  # Subdomain taken
                subdomain = lowered
            else:
                subdomain = self._generate_subdomain()
                while subdomain in self.subdomain_map:
                    subdomain = self._generate_subdomain()
            
            tunnel_id = self._generate_id()
            
            tunnel = Tunnel(
                tunnel_id=tunnel_id,
                subdomain=subdomain,
                websocket=websocket,
                local_port=local_port,
                tcp_enabled=bool(tcp_enabled),
                tcp_public_port=tcp_public_port or None,
                tcp_target_host=tcp_target_host or "127.0.0.1",
                tcp_target_port=tcp_target_port if tcp_target_port is not None else local_port,
            )
            
            self.tunnels[tunnel_id] = tunnel
            self.subdomain_map[subdomain] = tunnel_id
            
            return tunnel
    
    async def remove_tunnel(self, tunnel_id: str):
        """Remove tunnel"""
        async with self._get_lock():
            tunnel = self.tunnels.pop(tunnel_id, None)
            if tunnel:
                if tunnel.subdomain in self.subdomain_map:
                    del self.subdomain_map[tunnel.subdomain]
                tunnel.close()
    
    async def get_by_subdomain(self, subdomain: str) -> Optional[Tunnel]:
        """Get tunnel by subdomain"""
        async with self._get_lock():
            tunnel_id = self.subdomain_map.get(subdomain)
            return self.tunnels.get(tunnel_id) if tunnel_id else None
    
    async def get_by_id(self, tunnel_id: str) -> Optional[Tunnel]:
        """Get tunnel by ID"""
        async with self._get_lock():
            return self.tunnels.get(tunnel_id)
    
    async def forward_request(self, subdomain: str, method: str, path: str,
                             headers: Dict[str, str], body: Optional[str] = None,
                             body_b64: Optional[str] = None,
                             timeout: float = 30.0) -> Optional[Dict]:
        """Forward HTTP request through tunnel"""
        tunnel = await self.get_by_subdomain(subdomain)
        
        if not tunnel or not tunnel.is_active:
            return None
        
        request_id = self._generate_request_id()
        future = asyncio.get_event_loop().create_future()
        tunnel.add_request(request_id, future)
        
        # Import here to avoid circular import
        from tunnel.core.protocol import create_http_request
        
        message = create_http_request(request_id, method, path, headers, body, body_b64)
        
        try:
            await tunnel.websocket.send_text(message.to_json())
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            tunnel.complete_request(request_id, None)
            return {"status_code": 504, "headers": {}, "body": "Gateway Timeout"}
        except Exception as e:
            tunnel.complete_request(request_id, None)
            return {"status_code": 502, "headers": {}, "body": f"Bad Gateway: {str(e)}"}
    
    async def handle_response(self, tunnel_id: str, response_data: Dict):
        """Handle response from client"""
        tunnel = await self.get_by_id(tunnel_id)
        if tunnel:
            request_id = response_data.get("request_id")
            if request_id:
                tunnel.complete_request(request_id, response_data)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        async with self._get_lock():
            return {
                "total_tunnels": len(self.tunnels),
                "active_tunnels": sum(1 for t in self.tunnels.values() if t.is_active),
                "subdomains": list(self.subdomain_map.keys())
            }
    
    async def cleanup_stale(self, max_idle: float = 300):
        """Remove stale connections"""
        current_time = time.time()
        to_remove = []
        
        async with self._get_lock():
            for tunnel_id, tunnel in self.tunnels.items():
                if current_time - tunnel.last_ping > max_idle:
                    to_remove.append(tunnel_id)
        
        for tunnel_id in to_remove:
            await self.remove_tunnel(tunnel_id)
            logger.info(f"Removed stale tunnel: {tunnel_id}")
