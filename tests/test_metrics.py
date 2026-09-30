"""Metrics (prometheus_client) + X-Request-ID tracing."""

import pytest
import httpx

from tunnel.utils.metrics import MetricsCollector
from tunnel.utils.request_logger import RequestLogger


def test_record_and_prometheus_shape():
    m = MetricsCollector()
    m.record_request("GET", 200, 12.5)
    m.record_request("POST", 502, 1500.0)
    m.set_active_tunnels(2)
    d = m.to_dict()
    assert d["requests_total"] == 2
    assert d["requests_by_status"] == {200: 1, 502: 1}
    assert d["active_tunnels"] == 2
    text = m.to_prometheus_format()
    assert "tunnel_requests_total" in text
    assert "tunnel_active_tunnels 2" in text
    if m.use_prom:
        # standard prom exposition: labels + histogram buckets + _count/_sum
        assert 'method="GET"' in text and 'status="200"' in text
        assert "tunnel_request_duration_seconds_bucket" in text
        assert "tunnel_request_duration_seconds_count" in text
    else:
        assert "tunnel_requests_by_status" in text


def test_request_metrics_filter_and_bandwidth():
    logger = RequestLogger()
    logger.log(
        "GET",
        "/one",
        "app",
        "127.0.0.1",
        200,
        10,
        request_id="one",
        request_size=5,
        response_size=100,
    )
    logger.log(
        "POST",
        "/two",
        "app",
        "127.0.0.1",
        500,
        20,
        request_id="two",
        request_size=10,
        response_size=20,
    )
    stats = logger.get_stats_for(method="POST")
    assert stats["total_requests"] == 1
    assert stats["request_bytes"] == 10
    assert stats["response_bytes"] == 20


@pytest.mark.asyncio
async def test_metrics_endpoint_and_request_id(monkeypatch):
    from tunnel.server import app as appmod

    transport = httpx.ASGITransport(app=appmod.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/metrics")
        assert r.status_code == 200
        assert "tunnel_requests_total" in r.text
        assert "text/plain" in r.headers["content-type"]

        # 404 carries trace id
        r = await c.get("/nope", headers={"host": "unknown.test.dev"})
        assert r.status_code == 404
        assert r.headers["x-request-id"]

        # incoming trace id is echoed
        r = await c.get(
            "/nope", headers={"host": "unknown.test.dev", "x-request-id": "trace123"}
        )
        assert r.headers["x-request-id"] == "trace123"

        # success path echoes internal request_id
        async def fake_forward(**kwargs):
            return {
                "request_id": "req_abc",
                "status_code": 200,
                "headers": {"content-type": "text/plain"},
                "body": "ok",
                "body_b64": None,
            }

        monkeypatch.setattr(appmod.manager, "forward_request", fake_forward)
        t = await appmod.manager.create_tunnel(object(), 3000, "trace-t")
        try:
            r = await c.get("/y", headers={"host": "trace-t.test.dev"})
            assert r.headers["x-request-id"] == "req_abc"
        finally:
            await appmod.manager.remove_tunnel(t.tunnel_id)
