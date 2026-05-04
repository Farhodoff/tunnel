"""
Tests for tunnel client behavior
"""

import json
import asyncio

import aiohttp
import pytest
import websockets

from tunnel.client.tunnel_client import TunnelClient
from tunnel.core.protocol import (
    create_connect_ack,
    create_error,
    ErrorCode,
    MessageType,
)


class FakeWebSocket:
    def __init__(self, messages):
        self._messages = asyncio.Queue()
        for message in messages:
            self._messages.put_nowait(message)
        self.sent = []
        self.closed = False

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        return await self._messages.get()

    async def close(self):
        self.closed = True


class FakeResponse:
    def __init__(self, status=200, headers=None, body="ok"):
        self.status = status
        self.headers = headers or {"content-type": "text/plain"}
        self._body = body

    async def text(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, response=None, raise_error=None):
        self.response = response or FakeResponse()
        self.raise_error = raise_error
        self.request_calls = []
        self.closed = False

    def request(self, **kwargs):
        if self.raise_error:
            raise self.raise_error
        self.request_calls.append(kwargs)
        return self.response

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_connect_handles_error_message(monkeypatch):
    error_msg = create_error(ErrorCode.AUTH_FAILED, "Invalid token").to_json()
    ws = FakeWebSocket([error_msg])

    async def fake_connect(url):
        return ws

    monkeypatch.setattr(websockets, "connect", fake_connect)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeSession())

    client = TunnelClient("ws://localhost:8080", 3000)
    result = await client.connect()

    assert result is False
    assert client.connected is False


@pytest.mark.asyncio
async def test_connect_ack_sets_state(monkeypatch):
    ack_msg = create_connect_ack("tun_1", "mysub", "https://mysub.tunnel.dev").to_json()
    ws = FakeWebSocket([ack_msg])

    async def fake_connect(url):
        return ws

    monkeypatch.setattr(websockets, "connect", fake_connect)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeSession())

    client = TunnelClient("ws://localhost:8080", 3000, subdomain="mysub", auth_token="token")
    result = await client.connect()

    assert result is True
    assert client.connected is True
    assert client.tunnel_id == "tun_1"
    assert client.public_url == "https://mysub.tunnel.dev"
    assert client._ping_task is not None

    sent_payload = json.loads(ws.sent[0])
    assert sent_payload["msg_type"] == MessageType.CONNECT.value
    assert sent_payload["payload"]["local_port"] == 3000
    assert sent_payload["payload"]["subdomain"] == "mysub"
    assert sent_payload["payload"]["auth_token"] == "token"

    await client.disconnect()
    assert client.connected is False


@pytest.mark.asyncio
async def test_forward_request_filters_headers(monkeypatch):
    session = FakeSession(response=FakeResponse(status=201, headers={"x-test": "1"}, body="ok"))
    client = TunnelClient("ws://localhost:8080", 3000)
    client.session = session

    request_data = {
        "request_id": "req1",
        "method": "POST",
        "path": "/api",
        "headers": {"Host": "example.com", "Content-Length": "10", "X-Test": "1"},
        "body": "data",
    }

    response = await client._forward_request(request_data)

    assert response["status_code"] == 201
    assert response["body"] == "ok"

    sent_headers = session.request_calls[0]["headers"]
    assert "Host" not in sent_headers
    assert "Content-Length" not in sent_headers
    assert sent_headers["X-Test"] == "1"
