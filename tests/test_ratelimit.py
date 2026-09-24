"""Rate limiter: memory, env config, redis fallback + distribution."""

import time

from tunnel.utils.rate_limiter import RateLimiter


def test_memory_enforced_and_remaining():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    assert rl.backend == "memory"
    assert all(rl.is_allowed("ip1") for _ in range(3))
    assert rl.is_allowed("ip1") is False
    assert rl.get_remaining("ip1") == 0
    assert rl.is_allowed("ip2") is True  # per-key isolation


def test_env_config(monkeypatch):
    monkeypatch.setenv("TUNNEL_RATE_LIMIT", "7")
    monkeypatch.setenv("TUNNEL_RATE_WINDOW", "30")
    monkeypatch.delenv("TUNNEL_REDIS_URL", raising=False)
    rl = RateLimiter()
    rl.configure_from_env()
    assert rl.max_requests == 7
    assert rl.window_seconds == 30
    assert rl.backend == "memory"


def test_bad_redis_falls_back_to_memory():
    rl = RateLimiter(
        max_requests=2, window_seconds=60, redis_url="redis://127.0.0.1:9/0"
    )
    # connection refused -> fallback, still enforces via memory
    assert all(rl.is_allowed("k") for _ in range(2))
    assert rl.is_allowed("k") is False
    assert rl.backend in ("memory", "memory-fallback")


class FakeRedis:
    """Minimal redis stub sharing state across limiter instances."""

    store = {}

    def incr(self, k):
        self.store[k] = self.store.get(k, 0) + 1
        return self.store[k]

    def expire(self, k, ttl):
        return True

    def get(self, k):
        v = self.store.get(k)
        return str(v) if v is not None else None

    def ttl(self, k):
        return 60

    def ping(self):
        return True


def test_distributed_limit_shared_across_instances(monkeypatch):
    FakeRedis.store = {}
    rl1 = RateLimiter(max_requests=3, window_seconds=60, redis_url="redis://fake/0")
    rl2 = RateLimiter(max_requests=3, window_seconds=60, redis_url="redis://fake/0")
    fake = FakeRedis()
    monkeypatch.setattr(rl1, "_get_redis", lambda: fake)
    monkeypatch.setattr(rl2, "_get_redis", lambda: fake)
    assert rl1.is_allowed("shared") is True
    assert rl1.is_allowed("shared") is True
    assert rl2.is_allowed("shared") is True
    # 4th globally -> blocked on both
    assert rl1.is_allowed("shared") is False
    assert rl2.is_allowed("shared") is False
    assert rl2.get_remaining("shared") == 0
