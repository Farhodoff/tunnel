import httpx
import pytest

from tunnel.server.app import app
from tunnel.server.webhook_tester import WebhookStore


def test_webhook_store_persists_and_rejects_missing_endpoint(tmp_path):
    store = WebhookStore(storage_path=str(tmp_path / "webhooks.json"))
    endpoint = store.create_endpoint()
    assert store.get_requests(endpoint) == []
    with pytest.raises(KeyError):
        store.get_requests("missing")
    restored = WebhookStore(storage_path=str(tmp_path / "webhooks.json"))
    assert endpoint in restored._entries


@pytest.mark.asyncio
async def test_webhook_endpoint_returns_404_for_missing_capture():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhooks/capture/missing", content=b"{}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webhook_management_requires_auth(monkeypatch):
    from tunnel.auth.manager import auth_manager

    auth_manager._keys.clear()
    auth_manager._key_hashes.clear()
    auth_manager.disable()
    raw = auth_manager.generate_key("webhook-admin")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhooks/create")
        assert response.status_code == 401
        response = await client.post("/webhooks/create", headers={"X-API-Key": raw})
        assert response.status_code == 200
    auth_manager._keys.clear()
    auth_manager._key_hashes.clear()
    auth_manager.disable()
