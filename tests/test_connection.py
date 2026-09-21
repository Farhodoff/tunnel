import pytest

from tunnel.server.connection import ConnectionManager, validate_subdomain


def test_validate_reserved():
    for name in ["dashboard", "api", "metrics", "health", "webhooks", "www"]:
        ok, _ = validate_subdomain(name)
        assert ok is False


def test_validate_bad_format():
    for bad in ["Bad_Name!", "-lead", "trail-", "a" * 64, "UPPER CASE"]:
        ok, _ = validate_subdomain(bad)
        assert ok is False


def test_validate_ok():
    ok, _ = validate_subdomain("myapp-123")
    assert ok is True
    ok, _ = validate_subdomain(None)
    assert ok is True


@pytest.mark.asyncio
async def test_create_tunnel_rejects_reserved():
    m = ConnectionManager()
    assert await m.create_tunnel(object(), 3000, "dashboard") is None
    t = await m.create_tunnel(object(), 3000, "myapp-ok")
    assert t is not None
    assert t.subdomain == "myapp-ok"
    # taken
    assert await m.create_tunnel(object(), 3000, "myapp-ok") is None


@pytest.mark.asyncio
async def test_cleanup_stale_removes_idle():
    m = ConnectionManager()
    t = await m.create_tunnel(object(), 3000, "stale1")
    assert t is not None
    t.last_ping = t.last_ping - 1000
    await m.cleanup_stale(max_idle=10)
    assert await m.get_by_subdomain("stale1") is None


def test_public_url_scheme():
    m = ConnectionManager(base_domain="ex.com", use_https=True)
    assert m.get_public_url("a") == "https://a.ex.com"
    m.set_use_https(False)
    m.set_base_domain("my.dev")
    assert m.get_public_url("a") == "http://a.my.dev"
