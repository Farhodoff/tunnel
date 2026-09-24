"""TCP handler wiring tests."""

import asyncio

import pytest

from tunnel.server.connection import ConnectionManager
from tunnel.server.tcp_handler import TCPHandler


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, data: str):
        self.sent.append(data)


@pytest.mark.asyncio
async def test_tcp_listener_auto_port_and_relay():
    m = ConnectionManager()
    h = TCPHandler(m)
    ws = FakeWS()
    t = await m.create_tunnel(ws, 3000, "tcpecho1", tcp_enabled=True)
    assert t is not None

    # target = local echo server
    async def echo(reader, writer):
        data = await reader.read(1024)
        writer.write(b"echo:" + data)
        await writer.drain()
        writer.close()

    target = await asyncio.start_server(echo, "127.0.0.1", 0)
    target_port = target.sockets[0].getsockname()[1]

    server = await h.start_tcp_listener(0, t.tunnel_id, "127.0.0.1", target_port)
    public_port = h.get_listener_port(t.tunnel_id)
    assert public_port and public_port != target_port

    # emulate client side: server sends TCP_CONNECT, fake client connects to target,
    # sends TCP_DATA back, server relays to public connection
    # simpler: open real TCP connection to public port, check server queued TCP_CONNECT
    reader, writer = await asyncio.open_connection("127.0.0.1", public_port)
    await asyncio.sleep(0.2)
    assert ws.sent, "expected TCP_CONNECT message"
    import json

    connect_msg = json.loads(ws.sent[0])
    assert connect_msg["msg_type"] == "tcp_connect"
    cid = connect_msg["payload"]["connection_id"]

    # send data from public client -> should be forwarded as TCP_DATA(out)
    writer.write(b"hi")
    await writer.drain()
    await asyncio.sleep(0.2)
    assert len(ws.sent) >= 2
    data_msg = json.loads(ws.sent[1])
    assert data_msg["msg_type"] == "tcp_data"
    import base64

    assert base64.b64decode(data_msg["payload"]["data"]) == b"hi"

    # simulate client answering with data(in) -> relayed to public socket
    await h.handle_tcp_data(
        t.tunnel_id,
        {
            "connection_id": cid,
            "data": base64.b64encode(b"hello-back").decode(),
            "direction": "in",
        },
    )
    got = await asyncio.wait_for(reader.read(1024), timeout=2)
    assert got == b"hello-back"

    writer.close()
    await h.stop_tcp_listener(t.tunnel_id)
    target.close()
    await m.remove_tunnel(t.tunnel_id)


@pytest.mark.asyncio
async def test_tcp_port_conflict():
    m = ConnectionManager()
    h = TCPHandler(m)
    t1 = await m.create_tunnel(object(), 3000, "tcpconf1")
    t2 = await m.create_tunnel(object(), 3000, "tcpconf2")
    await h.start_tcp_listener(0, t1.tunnel_id, "127.0.0.1", 3000)
    used = h.get_listener_port(t1.tunnel_id)
    assert h.is_port_in_use(used) is True
    with pytest.raises(OSError):
        await h.start_tcp_listener(used, t2.tunnel_id, "127.0.0.1", 3000)
    await h.stop_tcp_listener(t1.tunnel_id)
    await h.stop_tcp_listener(t2.tunnel_id)
