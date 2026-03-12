"""
Core Protocol - Message definitions and serialization
"""

import json
import uuid
from enum import Enum, auto
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime


class MessageType(Enum):
    """Message types for tunnel communication"""
    # Connection
    CONNECT = "connect"
    CONNECT_ACK = "connect_ack"
    DISCONNECT = "disconnect"
    
    # Heartbeat
    PING = "ping"
    PONG = "pong"
    
    # HTTP
    HTTP_REQUEST = "http_request"
    HTTP_RESPONSE = "http_response"
    
    # TCP
    TCP_CONNECT = "tcp_connect"
    TCP_DATA = "tcp_data"
    TCP_CLOSE = "tcp_close"
    
    # Errors
    ERROR = "error"


class ErrorCode(Enum):
    """Error codes"""
    INVALID_MESSAGE = "invalid_message"
    AUTH_FAILED = "auth_failed"
    SUBDOMAIN_TAKEN = "subdomain_taken"
    TUNNEL_NOT_FOUND = "tunnel_not_found"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"


@dataclass
class Message:
    """Base message structure"""
    msg_type: str
    payload: Dict[str, Any]
    msg_id: str = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.msg_id is None:
            self.msg_id = str(uuid.uuid4())[:8]
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> "Message":
        parsed = json.loads(data)
        return cls(**parsed)
    
    @classmethod
    def create(cls, msg_type: MessageType, payload: Dict[str, Any]) -> "Message":
        return cls(msg_type=msg_type.value, payload=payload)


# Connection messages
@dataclass
class ConnectPayload:
    """Client connection request"""
    subdomain: Optional[str]
    local_port: int
    auth_token: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConnectAckPayload:
    """Server connection acknowledgment"""
    tunnel_id: str
    subdomain: str
    public_url: str
    status: str = "success"
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# HTTP messages
@dataclass
class HTTPRequestPayload:
    """HTTP request forwarded through tunnel"""
    request_id: str
    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HTTPResponsePayload:
    """HTTP response from local server"""
    request_id: str
    status_code: int
    headers: Dict[str, str]
    body: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# TCP messages
@dataclass
class TCPConnectPayload:
    """TCP connection request"""
    connection_id: str
    remote_host: str
    remote_port: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TCPDataPayload:
    """TCP data transfer"""
    connection_id: str
    data: str  # Base64 encoded
    direction: str  # "in" or "out"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TCPClosePayload:
    """TCP connection close"""
    connection_id: str
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Error message
@dataclass
class ErrorPayload:
    """Error message"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Helper functions
def create_connect_message(subdomain: Optional[str], local_port: int, 
                          auth_token: Optional[str] = None) -> Message:
    """Create connection request message"""
    payload = ConnectPayload(
        subdomain=subdomain,
        local_port=local_port,
        auth_token=auth_token
    )
    return Message.create(MessageType.CONNECT, payload.to_dict())


def create_connect_ack(tunnel_id: str, subdomain: str, public_url: str) -> Message:
    """Create connection acknowledgment"""
    payload = ConnectAckPayload(
        tunnel_id=tunnel_id,
        subdomain=subdomain,
        public_url=public_url
    )
    return Message.create(MessageType.CONNECT_ACK, payload.to_dict())


def create_http_request(request_id: str, method: str, path: str,
                       headers: Dict[str, str], body: Optional[str] = None) -> Message:
    """Create HTTP request message"""
    payload = HTTPRequestPayload(
        request_id=request_id,
        method=method,
        path=path,
        headers=headers,
        body=body
    )
    return Message.create(MessageType.HTTP_REQUEST, payload.to_dict())


def create_http_response(request_id: str, status_code: int,
                        headers: Dict[str, str], body: Optional[str] = None) -> Message:
    """Create HTTP response message"""
    payload = HTTPResponsePayload(
        request_id=request_id,
        status_code=status_code,
        headers=headers,
        body=body
    )
    return Message.create(MessageType.HTTP_RESPONSE, payload.to_dict())


def create_error(code: ErrorCode, message: str, details: Optional[Dict] = None) -> Message:
    """Create error message"""
    payload = ErrorPayload(
        code=code.value,
        message=message,
        details=details
    )
    return Message.create(MessageType.ERROR, payload.to_dict())


def create_ping() -> Message:
    """Create ping message"""
    return Message.create(MessageType.PING, {"timestamp": datetime.utcnow().isoformat()})


def create_pong(ping_timestamp: str) -> Message:
    """Create pong message"""
    return Message.create(MessageType.PONG, {
        "ping_timestamp": ping_timestamp,
        "timestamp": datetime.utcnow().isoformat()
    })


# TCP helper functions
def create_tcp_connect(connection_id: str, remote_host: str, remote_port: int) -> Message:
    """Create TCP connect message"""
    payload = TCPConnectPayload(
        connection_id=connection_id,
        remote_host=remote_host,
        remote_port=remote_port
    )
    return Message.create(MessageType.TCP_CONNECT, payload.to_dict())


def create_tcp_data(connection_id: str, data: str, direction: str = "out") -> Message:
    """Create TCP data message"""
    payload = TCPDataPayload(
        connection_id=connection_id,
        data=data,
        direction=direction
    )
    return Message.create(MessageType.TCP_DATA, payload.to_dict())


def create_tcp_close(connection_id: str, reason: Optional[str] = None) -> Message:
    """Create TCP close message"""
    payload = TCPClosePayload(
        connection_id=connection_id,
        reason=reason
    )
    return Message.create(MessageType.TCP_CLOSE, payload.to_dict())
