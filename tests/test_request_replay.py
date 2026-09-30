import httpx
import pytest

from tunnel.server.app import app
from tunnel.utils.request_logger import RequestLogger


def test_request_logger_stores_replay_payload():
    logger = RequestLogger()
    logger.log(
        "POST",
        "/hooks",
        "demo",
        "127.0.0.1",
        201,
        12.3,
        request_id="req-1",
        headers={"content-type": "application/json"},
        body='{"ok":true}',
        body_b64="eyJvayI6dHJ1ZX0=",
    )

    entry = logger.get_entry("req-1")
    assert entry is not None
    assert entry["headers"]["content-type"] == "application/json"
    assert entry["body_b64"] == "eyJvayI6dHJ1ZX0="
    assert logger.get_entry("missing") is None


@pytest.mark.asyncio
async def test_replay_log_forwards_original_request(monkeypatch):
    from tunnel.server import app as appmod

    appmod.request_logger.clear()
    appmod.request_logger.log(
        "POST",
        "/hooks?source=test",
        "replay-test",
        "127.0.0.1",
        200,
        1,
        request_id="req-replay",
        headers={"content-type": "application/json"},
        body=None,
        body_b64="e30=",
    )

    captured = {}

    async def fake_forward(**kwargs):
        captured.update(kwargs)
        return {
            "status_code": 202,
            "headers": {"x-replayed": "yes"},
            "body": "accepted",
            "body_b64": None,
        }

    monkeypatch.setattr(appmod.manager, "forward_request", fake_forward)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/logs/req-replay/replay")

    assert response.status_code == 200
    assert response.json()["status_code"] == 202
    assert captured["subdomain"] == "replay-test"
    assert captured["path"] == "/hooks?source=test"
    assert captured["body_b64"] == "e30="


@pytest.mark.asyncio
async def test_replay_log_returns_404_for_unknown_request():
    from tunnel.server import app as appmod

    appmod.request_logger.clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/logs/unknown/replay")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_replay_requires_api_key_when_auth_enabled():
    from tunnel.auth.manager import auth_manager
    from tunnel.server import app as appmod

    auth_manager._keys.clear()
    auth_manager._key_hashes.clear()
    auth_manager.disable()
    raw = auth_manager.generate_key("replay-admin")
    appmod.request_logger.clear()
    appmod.request_logger.log(
        "GET", "/", "replay-test", "127.0.0.1", 200, 1, request_id="protected"
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/logs/protected/replay")
        assert response.status_code == 401
        response = await client.post(
            "/api/logs/protected/replay", headers={"X-API-Key": raw}
        )
        assert response.status_code != 401
    auth_manager._keys.clear()
    auth_manager._key_hashes.clear()
    auth_manager.disable()


@pytest.mark.asyncio
async def test_proxy_rejects_oversized_body(monkeypatch):
    from tunnel.server import app as appmod

    original_limit = appmod.request_logger.max_body_bytes
    appmod.request_logger.max_body_bytes = 3
    tunnel = await appmod.manager.create_tunnel(object(), 3000, "body-limit")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/upload", content=b"too-large", headers={"host": "body-limit.test.dev"}
            )
        assert response.status_code == 413
    finally:
        appmod.request_logger.max_body_bytes = original_limit
        await appmod.manager.remove_tunnel(tunnel.tunnel_id)
