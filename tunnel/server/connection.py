"""
Server Connection Management
"""

import asyncio
import time
import uuid
from typing import Dict, Optional, Any
from dataclasses import dataclass, field


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
    
    def __init__(self, base_domain: str = "tunnel.dev"):
        self.base_domain = base_domain
        self.tunnels: Dict[str, Tunnel] = {}  # tunnel_id -> Tunnel
        self.subdomain_map: Dict[str, str] = {}  # subdomain -> tunnel_id
        self._lock = asyncio.Lock()
        self._request_counter = 0
    
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
    
    def get_public_url(self, subdomain: str) -> str:
        """Get public URL for subdomain"""
        return f"http://{subdomain}.{self.base_domain}"
    
    async def create_tunnel(self, websocket: Any, local_port: int,
                           requested_subdomain: Optional[str] = None) -> Optional[Tunnel]:
        """Create new tunnel"""
        async with self._lock:
            # Generate or validate subdomain
            if requested_subdomain:
                if requested_subdomain in self.subdomain_map:
                    return None  # Subdomain taken
                subdomain = requested_subdomain
            else:
                subdomain = self._generate_subdomain()
                while subdomain in self.subdomain_map:
                    subdomain = self._generate_subdomain()
            
            tunnel_id = self._generate_id()
            
            tunnel = Tunnel(
                tunnel_id=tunnel_id,
                subdomain=subdomain,
                websocket=websocket,
                local_port=local_port
            )
            
            self.tunnels[tunnel_id] = tunnel
            self.subdomain_map[subdomain] = tunnel_id
            
            return tunnel
    
    async def remove_tunnel(self, tunnel_id: str):
        """Remove tunnel"""
        async with self._lock:
            tunnel = self.tunnels.pop(tunnel_id, None)
            if tunnel:
                if tunnel.subdomain in self.subdomain_map:
                    del self.subdomain_map[tunnel.subdomain]
                tunnel.close()
    
    async def get_by_subdomain(self, subdomain: str) -> Optional[Tunnel]:
        """Get tunnel by subdomain"""
        async with self._lock:
            tunnel_id = self.subdomain_map.get(subdomain)
            return self.tunnels.get(tunnel_id) if tunnel_id else None
    
    async def get_by_id(self, tunnel_id: str) -> Optional[Tunnel]:
        """Get tunnel by ID"""
        async with self._lock:
            return self.tunnels.get(tunnel_id)
    
    async def forward_request(self, subdomain: str, method: str, path: str,
                             headers: Dict[str, str], body: Optional[str],
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
        
        message = create_http_request(request_id, method, path, headers, body)
        
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
        async with self._lock:
            return {
                "total_tunnels": len(self.tunnels),
                "active_tunnels": sum(1 for t in self.tunnels.values() if t.is_active),
                "subdomains": list(self.subdomain_map.keys())
            }
    
    async def cleanup_stale(self, max_idle: float = 300):
        """Remove stale connections"""
        current_time = time.time()
        to_remove = []
        
        async with self._lock:
            for tunnel_id, tunnel in self.tunnels.items():
                if current_time - tunnel.last_ping > max_idle:
                    to_remove.append(tunnel_id)
        
        for tunnel_id in to_remove:
            await self.remove_tunnel(tunnel_id)
            print(f"[ConnectionManager] Removed stale tunnel: {tunnel_id}")
