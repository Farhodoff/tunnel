"""Client hardening: no-leak connect, max retries, local target, config."""
import asyncio
import json

import pytest

import tunnel.cli as cli
from tunnel.client.tunnel_client import TunnelClient
from tunnel.core.protocol import create_connect_ack


class FakeWS:
    def __init__(self, messages):
        self._q = asyncio.Queue()
        for m in messages:
            self._q.put_nowait(m)
        self.sent = []
        self.closed = False

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        return await self._q.get()

    async def close(self):
        self.closed = True


class FakeSession:
    def __init__(self):
        self.closed = False
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)

        class R:
            status = 200
            headers = {}

            async def read(self):
                return b"ok"

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

        return R()

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_failed_handshake_closes_session_and_ws(monkeypatch):
    import websockets
    import aiohttp
    from tunnel.core.protocol import create_error, ErrorCode
    ws = FakeWS([create_error(ErrorCode.AUTH_FAILED, "no").to_json()])
    sessions = []

    async def fake_connect(url):
        return ws

    def fake_session():
        s = FakeSession()
        sessions.append(s)
        return s

    monkeypatch.setattr(websockets, "connect", fake_connect)
    monkeypatch.setattr(aiohttp, "ClientSession", fake_session)

    c = TunnelClient("ws://x:1", 3000)
    assert await c.connect() is False
    assert c.ws is None and c.session is None
    assert ws.closed is True and sessions[0].closed is True


@pytest.mark.asyncio
async def test_max_retries_exhausted_returns_1(monkeypatch):
    c = TunnelClient("ws://down:1", 3000, max_retries=2)
    calls = {"n": 0}

    async def fail():
        calls["n"] += 1
        return False

    monkeypatch.setattr(c, "connect", fail)
    rc = await c.run()
    assert rc == 1 and calls["n"] == 2


@pytest.mark.asyncio
async def test_local_host_and_scheme_used():
    c = TunnelClient("ws://x", 3000, local_host="10.0.0.5", local_https=True, insecure=True)
    c.session = FakeSession()
    out = await c._forward_request({"request_id": "r", "method": "GET",
                                    "path": "/a", "headers": {}, "body": None})
    assert out["status_code"] == 200
    assert c.session.calls[0]["url"] == "https://10.0.0.5:3000/a"
    assert c.session.calls[0]["ssl"] is False


def test_config_file_merge(tmp_path, monkeypatch, capsys):
    cfg = {"server": "ws://cfg:9", "local_port": 4000, "subdomain": "fromcfg",
           "token": "tok", "local_host": "10.1.1.1", "reconnect": {"max_attempts": 5}}
    p = tmp_path / "c.json"
    p.write_text(json.dumps(cfg))
    import sys
    monkeypatch.setattr(sys, "argv", ["cli", "--config", str(p)])

    created = {}

    class FakeClient:
        def __init__(self, **kw):
            created.update(kw)

        async def run(self):
            return 0

    monkeypatch.setattr(cli, "TunnelClient", FakeClient)
    with pytest.raises(SystemExit) as e:
        cli.run_client()
    assert e.value.code == 0
    assert created["server_url"] == "ws://cfg:9"
    assert created["local_port"] == 4000
    assert created["subdomain"] == "fromcfg"
    assert created["auth_token"] == "tok"
    assert created["local_host"] == "10.1.1.1"
    assert created["max_retries"] == 5
