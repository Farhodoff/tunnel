"""
Rate Limiter - Request throttling (memory + optional Redis backend)
"""

import os
import time
from typing import Dict, Optional
from dataclasses import dataclass, field

from tunnel.utils.logging import setup_logger

logger = setup_logger("tunnel.ratelimiter")


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry (memory fallback)"""
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    
    def reset(self):
        """Reset counter"""
        self.requests = 0
        self.window_start = time.time()


class RateLimiter:
    """Fixed-window rate limiter with Redis backend + memory fallback"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60,
                 redis_url: Optional[str] = None, prefix: str = "tunelimit:"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_url = redis_url or None
        self.prefix = prefix
        self._entries: Dict[str, RateLimitEntry] = {}
        self._redis = None
        self._redis_failed = False

    # -- configuration --
    def configure(self, max_requests: Optional[int] = None,
                  window_seconds: Optional[int] = None,
                  redis_url: Optional[str] = None):
        """Update settings at runtime (e.g. from CLI/env)"""
        if max_requests is not None:
            self.max_requests = max_requests
        if window_seconds is not None:
            self.window_seconds = window_seconds
        if redis_url is not None:
            self.redis_url = redis_url or None
            self._redis = None
            self._redis_failed = False

    def configure_from_env(self, prefix: str = "TUNNEL_"):
        """Read TUNNEL_RATE_LIMIT / TUNNEL_RATE_WINDOW / TUNNEL_REDIS_URL"""
        try:
            max_r = int(os.getenv(f"{prefix}RATE_LIMIT", str(self.max_requests)))
        except ValueError:
            max_r = self.max_requests
        try:
            win = int(os.getenv(f"{prefix}RATE_WINDOW", str(self.window_seconds)))
        except ValueError:
            win = self.window_seconds
        redis_url = os.getenv(f"{prefix}REDIS_URL", self.redis_url or "")
        self.configure(max_requests=max_r, window_seconds=win,
                       redis_url=redis_url or None)
        return self

    @property
    def backend(self) -> str:
        """Active backend name for observability"""
        if self._redis is not None and not self._redis_failed:
            return "redis"
        if self.redis_url:
            return "redis" if not self._redis_failed else "memory-fallback"
        return "memory"

    # -- redis plumbing (lazy, optional dep) --
    def _get_redis(self):
        if not self.redis_url or self._redis_failed:
            return None
        if self._redis is not None:
            return self._redis
        try:
            import redis  # optional dependency
            client = redis.StrictRedis.from_url(self.redis_url, decode_responses=True)
            client.ping()
            self._redis = client
            return client
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), using memory fallback")
            self._redis_failed = True
            return None

    def _window_key(self, key: str) -> str:
        window_id = int(time.time() // self.window_seconds)
        return f"{self.prefix}{key}:{window_id}"

    # -- memory path --
    def _memory_allowed(self, key: str) -> bool:
        current_time = time.time()
        entry = self._entries.get(key)
        if not entry:
            entry = RateLimitEntry()
            self._entries[key] = entry
        if current_time - entry.window_start > self.window_seconds:
            entry.reset()
        if entry.requests >= self.max_requests:
            return False
        entry.requests += 1
        return True

    # -- public API (same as before) --
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        r = self._get_redis()
        if r is None:
            return self._memory_allowed(key)
        try:
            k = self._window_key(key)
            count = r.incr(k)
            if count == 1:
                r.expire(k, self.window_seconds * 2)
            return count <= self.max_requests
        except Exception as e:
            logger.warning(f"Redis error ({e}), fallback to memory")
            self._redis_failed = True
            return self._memory_allowed(key)
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests in window"""
        r = self._get_redis()
        if r is not None:
            try:
                count = r.get(self._window_key(key))
                used = int(count) if count else 0
                return max(0, self.max_requests - used)
            except Exception:
                pass
        entry = self._entries.get(key)
        if not entry:
            return self.max_requests
        if time.time() - entry.window_start > self.window_seconds:
            return self.max_requests
        return max(0, self.max_requests - entry.requests)
    
    def get_reset_time(self, key: str) -> float:
        """Get time when limit resets"""
        r = self._get_redis()
        if r is not None:
            try:
                ttl = r.ttl(self._window_key(key))
                if ttl and ttl > 0:
                    return time.time() + ttl
            except Exception:
                pass
        entry = self._entries.get(key)
        if not entry:
            return time.time()
        return entry.window_start + self.window_seconds
    
    def cleanup(self, max_age: float = 300):
        """Remove old memory entries (Redis keys expire automatically)"""
        current_time = time.time()
        to_remove = [
            key for key, entry in self._entries.items()
            if current_time - entry.window_start > max_age
        ]
        for key in to_remove:
            del self._entries[key]


# Global rate limiter (env-driven; Redis optional)
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
rate_limiter.configure_from_env()
