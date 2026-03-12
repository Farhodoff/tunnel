"""
Bandwidth Limiter - Control data transfer rates
"""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class BandwidthCounter:
    """Track bandwidth usage"""
    bytes_sent: int = 0
    bytes_received: int = 0
    window_start: float = field(default_factory=time.time)
    
    def reset(self):
        """Reset counter"""
        self.bytes_sent = 0
        self.bytes_received = 0
        self.window_start = time.time()
    
    def add_sent(self, bytes_count: int):
        """Add sent bytes"""
        self.bytes_sent += bytes_count
    
    def add_received(self, bytes_count: int):
        """Add received bytes"""
        self.bytes_received += bytes_count


class BandwidthLimiter:
    """Limit bandwidth per tunnel"""
    
    def __init__(self, default_limit_kbps: int = 1000):  # 1 Mbps default
        self.default_limit_kbps = default_limit_kbps
        self._limits: Dict[str, int] = {}  # tunnel_id -> limit in kbps
        self._counters: Dict[str, BandwidthCounter] = {}
        self._window_seconds = 1
    
    def set_limit(self, tunnel_id: str, limit_kbps: int):
        """Set bandwidth limit for tunnel"""
        self._limits[tunnel_id] = limit_kbps
        if tunnel_id not in self._counters:
            self._counters[tunnel_id] = BandwidthCounter()
    
    def get_limit(self, tunnel_id: str) -> int:
        """Get bandwidth limit for tunnel"""
        return self._limits.get(tunnel_id, self.default_limit_kbps)
    
    async def throttle(self, tunnel_id: str, bytes_to_send: int, direction: str = "out"):
        """Throttle data transfer if needed"""
        limit_kbps = self.get_limit(tunnel_id)
        
        if limit_kbps <= 0:  # Unlimited
            return
        
        # Get or create counter
        if tunnel_id not in self._counters:
            self._counters[tunnel_id] = BandwidthCounter()
        
        counter = self._counters[tunnel_id]
        
        # Check if window expired
        current_time = time.time()
        if current_time - counter.window_start > self._window_seconds:
            counter.reset()
        
        # Calculate current rate
        current_bytes = counter.bytes_sent if direction == "out" else counter.bytes_received
        limit_bytes = (limit_kbps * 1024) / 8 * self._window_seconds  # Convert kbps to bytes per window
        
        # If over limit, wait
        if current_bytes >= limit_bytes:
            sleep_time = self._window_seconds - (current_time - counter.window_start)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                counter.reset()
        
        # Update counter
        if direction == "out":
            counter.add_sent(bytes_to_send)
        else:
            counter.add_received(bytes_to_send)
    
    def get_usage(self, tunnel_id: str) -> Optional[Dict]:
        """Get bandwidth usage for tunnel"""
        counter = self._counters.get(tunnel_id)
        if not counter:
            return None
        
        return {
            "bytes_sent": counter.bytes_sent,
            "bytes_received": counter.bytes_received,
            "limit_kbps": self.get_limit(tunnel_id)
        }
    
    def remove_tunnel(self, tunnel_id: str):
        """Remove tunnel from tracking"""
        self._limits.pop(tunnel_id, None)
        self._counters.pop(tunnel_id, None)


# Global bandwidth limiter
bandwidth_limiter = BandwidthLimiter(default_limit_kbps=1000)
