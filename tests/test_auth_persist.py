"""Auth persistence + /api/keys REST."""
import json

import pytest
import httpx

from tunnel.auth.manager import AuthManager
from tunnel.server.app import app
from tunnel.auth.manager import auth_manager


def test_save_load_roundtrip(tmp_path):
    f = str(tmp_path / "keys.json")
    m1 = AuthManager(file_path=f)
    raw = m1.generate_key("test-key")
    # generating a key enables auth (fail-closed)
    assert m1.is_enabled is True
    assert m1.validate_key(raw) is True
    assert m1.validate_key("wrong") is False

    # file written on generate
    data = json.loads(open(f).read())
    assert len(data) == 1 and data[0]["name"] == "test-key"

    # new manager loads from file -> validates without raw re-entry
    m2 = AuthManager(file_path=f)
    assert m2.load_from_file(f) == 1
    assert m2.validate_key(raw) is True

    # revoke persists
    key_id = data[0]["key_id"]
    assert m2.revoke_key(key_id) is True
    assert m2.validate_key(raw) is False
    m3 = AuthManager(file_path=f)
    assert m3.load_from_file(f) == 1
    assert m3.validate_key(raw) is False


def test_env_keys_not_persisted(tmp_path, monkeypatch):
    f = str(tmp_path / "keys.json")
    monkeypatch.setenv("TUNNEL_API_KEYS", "env-secret-1")
    monkeypatch.setenv("TUNNEL_API_KEYS_FILE", f)
    m = AuthManager()
    m.configure_from_env()
    assert m.is_enabled
    assert m.validate_key("env-secret-1") is True
    # env keys must not leak into the state file
    import os
    assert not os.path.exists(f) or "env-secret" not in open(f).read() if os.path.exists(f) else True


@pytest.mark.asyncio
async def test_keys_api_bootstrap_and_protected(monkeypatch):
    # isolated manager state for the app
    auth_manager._keys.clear()
    auth_manager._key_hashes.clear()
    auth_manager.disable()
    auth_manager.configure_file(None)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # bootstrap open: create first key
        r = await c.post("/api/keys", json={"name": "admin"})
        assert r.status_code == 200, r.text
        body = r.json()
        raw = body["api_key"]
        assert raw.startswith("tun_")

        # now auth enabled -> list without key = 401
        r = await c.get("/api/keys")
        assert r.status_code == 401

        # list with key = 200
        r = await c.get("/api/keys", headers={"X-API-Key": raw})
        assert r.status_code == 200
        assert body["key_id"] in r.json()["keys"]

        # revoke with Bearer auth
        r = await c.delete(f"/api/keys/{body['key_id']}",
                           headers={"Authorization": f"Bearer {raw}"})
        assert r.status_code == 200
        r = await c.get("/api/keys", headers={"X-API-Key": raw})
        assert r.status_code == 401

    auth_manager._keys.clear()
    auth_manager._key_hashes.clear()
    auth_manager.disable()
