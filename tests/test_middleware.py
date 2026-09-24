"""Middleware + logging wiring tests."""

import logging

import httpx
import pytest

from tunnel.server.app import app
from tunnel.utils.logging import _level_from_env
from tunnel.utils.middleware import request_modifier, response_modifier


def test_response_middleware_adds_cors_and_security():
    out = response_modifier.modify_headers({"content-type": "application/json"}, None)
    assert out["Access-Control-Allow-Origin"] == "*"
    assert out["X-Content-Type-Options"] == "nosniff"
    assert out["X-Frame-Options"] == "DENY"
    assert out["content-type"] == "application/json"  # upstream preserved


def test_request_middleware_passthrough_by_default():
    headers = {"host": "x", "x-a": "1"}
    assert request_modifier.modify_headers(dict(headers))["x-a"] == "1"
    assert request_modifier.rewrite_path("/a?b=1", "GET") == "/a?b=1"


def test_log_level_from_env(monkeypatch):
    monkeypatch.setenv("TUNNEL_LOG_LEVEL", "DEBUG")
    assert _level_from_env() == logging.DEBUG
    monkeypatch.setenv("TUNNEL_LOG_LEVEL", "bogus")
    assert _level_from_env() == logging.INFO


@pytest.mark.asyncio
async def test_proxy_response_carries_middleware_headers(monkeypatch):
    from tunnel.server import app as appmod

    async def fake_forward(**kwargs):
        return {
            "status_code": 200,
            "headers": {"content-type": "text/plain"},
            "body": "hi",
            "body_b64": None,
        }

    monkeypatch.setattr(appmod.manager, "forward_request", fake_forward)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # create a tunnel first so proxy finds it
        t = await appmod.manager.create_tunnel(object(), 3000, "midtest")
        try:
            r = await c.get("/x", headers={"host": "midtest.test.dev"})
            assert r.status_code == 200
            assert r.headers["access-control-allow-origin"] == "*"
            assert r.headers["x-content-type-options"] == "nosniff"
        finally:
            await appmod.manager.remove_tunnel(t.tunnel_id)
