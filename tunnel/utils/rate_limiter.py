"""
Rate Limiter - Request throttling
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry"""
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    
    def reset(self):
        """Reset counter"""
        self.requests = 0
        self.window_start = time.time()


class RateLimiter:
    """Simple sliding window rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._entries: Dict[str, RateLimitEntry] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        current_time = time.time()
        
        # Get or create entry
        entry = self._entries.get(key)
        if not entry:
            entry = RateLimitEntry()
            self._entries[key] = entry
        
        # Check if window expired
        if current_time - entry.window_start > self.window_seconds:
            entry.reset()
        
        # Check limit
        if entry.requests >= self.max_requests:
            return False
        
        # Increment counter
        entry.requests += 1
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests in window"""
        entry = self._entries.get(key)
        if not entry:
            return self.max_requests
        
        # Check if window expired
        if time.time() - entry.window_start > self.window_seconds:
            return self.max_requests
        
        return max(0, self.max_requests - entry.requests)
    
    def get_reset_time(self, key: str) -> float:
        """Get time when limit resets"""
        entry = self._entries.get(key)
        if not entry:
            return time.time()
        
        return entry.window_start + self.window_seconds
    
    def cleanup(self, max_age: float = 300):
        """Remove old entries"""
        current_time = time.time()
        to_remove = [
            key for key, entry in self._entries.items()
            if current_time - entry.window_start > max_age
        ]
        for key in to_remove:
            del self._entries[key]


# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
