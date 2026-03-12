# Tunnel API Documentation

## WebSocket Protocol

### Connection

Connect to `wss://tunnel.example.com/tunnel` (or `ws://` for non-SSL).

### Message Format

All messages are JSON with the following structure:

```json
{
  "msg_type": "connect",
  "payload": {},
  "msg_id": "abc123",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Message Types

#### Client → Server

**CONNECT**
```json
{
  "msg_type": "connect",
  "payload": {
    "subdomain": "myapp",
    "local_port": 3000,
    "auth_token": "optional_api_key"
  }
}
```

**HTTP_RESPONSE**
```json
{
  "msg_type": "http_response",
  "payload": {
    "request_id": "req123",
    "status_code": 200,
    "headers": {"content-type": "application/json"},
    "body": "response body"
  }
}
```

**TCP_DATA**
```json
{
  "msg_type": "tcp_data",
  "payload": {
    "connection_id": "conn123",
    "data": "base64_encoded_data",
    "direction": "in"
  }
}
```

#### Server → Client

**CONNECT_ACK**
```json
{
  "msg_type": "connect_ack",
  "payload": {
    "tunnel_id": "tun_abc123",
    "subdomain": "myapp",
    "public_url": "https://myapp.tunnel.example.com"
  }
}
```

**HTTP_REQUEST**
```json
{
  "msg_type": "http_request",
  "payload": {
    "request_id": "req123",
    "method": "GET",
    "path": "/api/users",
    "headers": {"host": "myapp.tunnel.example.com"},
    "body": null
  }
}
```

**TCP_CONNECT**
```json
{
  "msg_type": "tcp_connect",
  "payload": {
    "connection_id": "conn123",
    "remote_host": "localhost",
    "remote_port": 22
  }
}
```

## REST API

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "tunnels": {
    "total_tunnels": 5,
    "active_tunnels": 3
  }
}
```

### List Tunnels

```http
GET /api/tunnels
```

Response:
```json
{
  "total_tunnels": 5,
  "active_tunnels": 3,
  "subdomains": ["app1", "app2", "app3"]
}
```

### Get Logs

```http
GET /api/logs?limit=100&subdomain=myapp
```

Response:
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T00:00:00",
      "method": "GET",
      "path": "/api/users",
      "subdomain": "myapp",
      "client_ip": "192.168.1.1",
      "status_code": 200,
      "duration_ms": 45.2
    }
  ],
  "stats": {
    "total_requests": 1000,
    "avg_duration_ms": 52.3,
    "status_codes": {"200": 950, "404": 50}
  }
}
```

### Metrics

```http
GET /metrics
```

Returns Prometheus-formatted metrics.

### Create Webhook

```http
POST /webhooks/create
```

Response:
```json
{
  "endpoint_id": "abc123",
  "url": "/webhooks/capture/abc123",
  "full_url": "https://tunnel.example.com/webhooks/capture/abc123"
}
```

### Get Webhook Requests

```http
GET /webhooks/requests/{endpoint_id}?limit=50
```

Response:
```json
{
  "endpoint_id": "abc123",
  "requests": [
    {
      "id": "req1",
      "timestamp": "2024-01-01T00:00:00",
      "method": "POST",
      "path": "...",
      "headers": {},
      "body": "..."
    }
  ],
  "count": 1
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `invalid_message` | Invalid message format |
| `auth_failed` | Authentication failed |
| `subdomain_taken` | Subdomain already in use |
| `tunnel_not_found` | Tunnel not found |
| `timeout` | Request timeout |
| `internal_error` | Internal server error |

## Rate Limits

- HTTP requests: 100 per minute per IP
- WebSocket messages: 1000 per minute per connection
- Webhook creation: 10 per minute per IP
