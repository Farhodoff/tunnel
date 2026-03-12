"""
Tests for protocol module
"""

import pytest
import json
from tunnel.core.protocol import (
    Message, MessageType, ErrorCode,
    create_connect_message, create_connect_ack,
    create_http_request, create_http_response,
    create_error, create_ping, create_pong,
    create_tcp_connect, create_tcp_data, create_tcp_close
)


class TestMessage:
    def test_message_creation(self):
        msg = Message.create(MessageType.CONNECT, {"test": "data"})
        assert msg.msg_type == "connect"
        assert msg.payload == {"test": "data"}
        assert msg.msg_id is not None
        assert msg.timestamp is not None
    
    def test_message_to_json(self):
        msg = Message.create(MessageType.CONNECT, {"test": "data"})
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        assert parsed["msg_type"] == "connect"
        assert parsed["payload"] == {"test": "data"}
    
    def test_message_from_json(self):
        data = '{"msg_type": "connect", "payload": {"test": "data"}, "msg_id": "abc123", "timestamp": "2024-01-01T00:00:00"}'
        msg = Message.from_json(data)
        assert msg.msg_type == "connect"
        assert msg.payload == {"test": "data"}
        assert msg.msg_id == "abc123"


class TestConnectMessage:
    def test_create_connect_message(self):
        msg = create_connect_message("mysubdomain", 3000, "mytoken")
        assert msg.msg_type == "connect"
        assert msg.payload["subdomain"] == "mysubdomain"
        assert msg.payload["local_port"] == 3000
        assert msg.payload["auth_token"] == "mytoken"
    
    def test_create_connect_ack(self):
        msg = create_connect_ack("tun_123", "mysubdomain", "https://mysubdomain.tunnel.dev")
        assert msg.msg_type == "connect_ack"
        assert msg.payload["tunnel_id"] == "tun_123"
        assert msg.payload["subdomain"] == "mysubdomain"
        assert msg.payload["public_url"] == "https://mysubdomain.tunnel.dev"


class TestHTTPMessages:
    def test_create_http_request(self):
        msg = create_http_request("req123", "GET", "/api/users", {"host": "test.com"}, None)
        assert msg.msg_type == "http_request"
        assert msg.payload["request_id"] == "req123"
        assert msg.payload["method"] == "GET"
        assert msg.payload["path"] == "/api/users"
    
    def test_create_http_response(self):
        msg = create_http_response("req123", 200, {"content-type": "application/json"}, '{"ok": true}')
        assert msg.msg_type == "http_response"
        assert msg.payload["request_id"] == "req123"
        assert msg.payload["status_code"] == 200


class TestTCPMessages:
    def test_create_tcp_connect(self):
        msg = create_tcp_connect("conn123", "localhost", 22)
        assert msg.msg_type == "tcp_connect"
        assert msg.payload["connection_id"] == "conn123"
        assert msg.payload["remote_host"] == "localhost"
        assert msg.payload["remote_port"] == 22
    
    def test_create_tcp_data(self):
        msg = create_tcp_data("conn123", "dGVzdA==", "out")
        assert msg.msg_type == "tcp_data"
        assert msg.payload["connection_id"] == "conn123"
        assert msg.payload["data"] == "dGVzdA=="
        assert msg.payload["direction"] == "out"
    
    def test_create_tcp_close(self):
        msg = create_tcp_close("conn123", "Connection reset")
        assert msg.msg_type == "tcp_close"
        assert msg.payload["connection_id"] == "conn123"
        assert msg.payload["reason"] == "Connection reset"


class TestErrorMessage:
    def test_create_error(self):
        msg = create_error(ErrorCode.AUTH_FAILED, "Invalid token")
        assert msg.msg_type == "error"
        assert msg.payload["code"] == "auth_failed"
        assert msg.payload["message"] == "Invalid token"


class TestHeartbeat:
    def test_create_ping(self):
        msg = create_ping()
        assert msg.msg_type == "ping"
        assert "timestamp" in msg.payload
    
    def test_create_pong(self):
        msg = create_pong("2024-01-01T00:00:00")
        assert msg.msg_type == "pong"
        assert msg.payload["ping_timestamp"] == "2024-01-01T00:00:00"
        assert "timestamp" in msg.payload
