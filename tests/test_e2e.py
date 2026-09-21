"""E2E: manager forward + REST + WS validation (TestClient-free)."""
import asyncio
import base64
import json

import pytest
import httpx

from tunnel.server.app import app, manager
from tunnel.core.protocol import Message, MessageType


class FakeWS:
    """Server-side fake websocket (send_text -> queue for client task)."""
    def __init__(self):
        self.outbox = asyncio.Queue()
        self.sent_to_client = []

    async def send_text(self, data: str):
        await self.outbox.put(data)


@pytest.mark.asyncio
async def test_forward_http_binary_roundtrip():
    from tunnel.server.connection import ConnectionManager
    m = ConnectionManager(base_domain="e2e.dev")
    ws = FakeWS()
    tunnel = await m.create_tunnel(ws, 3000, "e2ebin")
    assert tunnel is not None

    raw_req = bytes(range(256))

    async def fake_client():
        # wait for http_request from server, echo back as binary response
        data = await ws.outbox.get()
        msg = Message.from_json(data)
        assert msg.msg_type == MessageType.HTTP_REQUEST.value
        payload = msg.payload
        # client decodes body_b64
        got = base64.b64decode(payload["body_b64"])
        assert got == raw_req
        # respond with binary + custom header
        resp_body = b"resp:" + got[:10]
        await m.handle_response(tunnel.tunnel_id, {
            "request_id": payload["request_id"],
            "status_code": 200,
            "headers": {"content-type": "application/octet-stream", "x-custom": "e2e-ok"},
            "body": "",
            "body_b64": base64.b64encode(resp_body).decode(),
        })

    task = asyncio.create_task(fake_client())
    resp = await m.forward_request(
        "e2ebin", "POST", "/echo?x=1",
        {"content-type": "application/octet-stream"},
        body=None,
        body_b64=base64.b64encode(raw_req).decode(),
    )
    await task
    assert resp["status_code"] == 200
    assert resp["headers"]["x-custom"] == "e2e-ok"
    assert base64.b64decode(resp["body_b64"]) == b"resp:" + raw_req[:10]
    await m.remove_tunnel(tunnel.tunnel_id)


@pytest.mark.asyncio
async def test_rest_health_and_tunnels():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"
        r = await c.get("/api/tunnels")
        assert r.status_code == 200
        body = r.json()
        assert "subdomains" in body
        assert "base_domain" in body


@pytest.mark.asyncio
async def test_ws_validation_reserved_and_taken():
    # mirrors app.websocket_endpoint validation order
    from tunnel.server.connection import validate_subdomain, ConnectionManager
    m = ConnectionManager()
    ok, reason = validate_subdomain("dashboard")
    assert not ok and "reserved" in reason.lower()
    t = await m.create_tunnel(object(), 3000, "e2etaken123")
    assert t is not None
    # taken -> create returns None (app maps to SUBDOMAIN_TAKEN error)
    assert await m.create_tunnel(object(), 3000, "e2etaken123") is None
    await m.remove_tunnel(t.tunnel_id)
