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

Bodies are binary-safe: raw bytes travel as base64 in `body_b64`
(with a UTF-8 `body` fallback for backward compatibility).

### Message Types

#### Client → Server

**CONNECT**
```json
{
  "msg_type": "connect",
  "payload": {
    "subdomain": "myapp",
    "local_port": 3000,
    "auth_token": "optional_api_key",
    "tcp_enabled": false,
    "tcp_public_port": 0,
    "tcp_target_host": "127.0.0.1",
    "tcp_target_port": 3000
  }
}
```

- `subdomain` is lowercased by the server. Reserved names are rejected
  with `invalid_message`: `www, api, dashboard, metrics, health, webhooks,
  webhook, admin, static, assets, tunnel, mail, ftp, localhost`.
  Allowed shape: `^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$`.
- `tcp_public_port: 0` = auto-assign. The actual port comes back in `CONNECT_ACK`.

**HTTP_RESPONSE**
```json
{
  "msg_type": "http_response",
  "payload": {
    "request_id": "req123",
    "status_code": 200,
    "headers": {"content-type": "application/json"},
    "body": "response body",
    "body_b64": "base64_encoded_raw_bytes"
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

Directions: `out` = public side → local service, `in` = local service → public side.

#### Server → Client

**CONNECT_ACK**
```json
{
  "msg_type": "connect_ack",
  "payload": {
    "tunnel_id": "tun_abc123",
    "subdomain": "myapp",
    "public_url": "https://myapp.tunnel.example.com",
    "tcp_port": 19000,
    "tcp_public_url": "tcp://tunnel.example.com:19000"
  }
}
```

`tcp_port` / `tcp_public_url` are `null` unless TCP was requested.

**HTTP_REQUEST**
```json
{
  "msg_type": "http_request",
  "payload": {
    "request_id": "req123",
    "method": "GET",
    "path": "/api/users",
    "headers": {"host": "myapp.tunnel.example.com"},
    "body": null,
    "body_b64": null
  }
}
```

**TCP_CONNECT**
```json
{
  "msg_type": "tcp_connect",
  "payload": {
    "connection_id": "conn123",
    "remote_host": "127.0.0.1",
    "remote_port": 22
  }
}
```

## REST API

Every proxied response (and 400/404/429/502 errors) carries an
`X-Request-ID` header: the internal `request_id` on success, otherwise the
incoming `X-Request-ID` or a generated id. Proxied responses also include
CORS (`Access-Control-Allow-*`) and security headers
(`X-Content-Type-Options`, `X-Frame-Options`).

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
  "subdomains": ["app1", "app2", "app3"],
  "base_domain": "tunnel.example.com",
  "use_https": true
}
```

### API Keys (auth persistence)

Keys survive restarts via `TUNNEL_API_KEYS_FILE` (JSON, hashes only).
While no keys exist the endpoints are open (bootstrap); afterwards a valid
key is required via `X-API-Key` or `Authorization: Bearer <key>`.

```http
GET /api/keys
POST /api/keys        {"name": "ci", "expires_in_days": 30}
DELETE /api/keys/{key_id}
```

Create responds with the raw key **once**:
```json
{
  "key_id": "d0c38ea448e2b437",
  "api_key": "tun_...",
  "name": "ci",
  "expires_in_days": 30
}
```

### Get Logs

```http
GET /api/logs?limit=100&subdomain=myapp
```

Supported filters are `subdomain`, `method`, `status_code`, `path`, and
`since` (seconds). Each log entry contains `request_size` and
`response_size`; the response statistics include aggregate bandwidth totals.

### Dashboard Metrics

```http
GET /api/metrics?since=3600&subdomain=myapp
```

Returns a time series of request latency, status codes, request sizes, and
response sizes for the dashboard.

### Custom Domains

Set `TUNNEL_CUSTOM_DOMAINS=api.example.com=myapp` to route that exact host to
the `myapp` tunnel. Point the domain's DNS record to the server and include it
in the reverse proxy's `server_name`; wildcard tunnel domains continue to use
`TUNNEL_DOMAIN`.

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

### Replay a Captured Request

```http
POST /api/logs/{request_id}/replay
```

Replays the captured request through the original tunnel and returns the
upstream status, headers, response body, and replay duration. Request logs
include the request headers and binary-safe body fields (`body` and
`body_b64`) so the dashboard can inspect and replay recent traffic.

### Metrics

```http
GET /metrics
```

Prometheus exposition (via `prometheus_client`):

- `tunnel_requests_total{method,status}`
- `tunnel_request_duration_seconds_bucket/_count/_sum` (standard `le` buckets)
- `tunnel_active_tunnels`

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

Webhook endpoint creation and request inspection require an API key when
authentication is enabled. Capture URLs return `404` for unknown endpoints,
are rate-limited by client IP, and reject bodies over `TUNNEL_WEBHOOK_MAX_BODY`.

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
| `invalid_message` | Invalid message format, reserved/bad subdomain, bad TCP port |
| `auth_failed` | Authentication failed |
| `subdomain_taken` | Subdomain already in use (also used for taken TCP ports) |
| `tunnel_not_found` | Tunnel not found |
| `timeout` | Request timeout |
| `internal_error` | Internal server error (e.g. TCP listen failed) |

## Rate Limits

Defaults (env-overridable: `TUNNEL_RATE_LIMIT`, `TUNNEL_RATE_WINDOW`,
`TUNNEL_REDIS_URL` for distributed limiting):

- HTTP requests: 100 per minute per IP
- WebSocket messages: 1000 per minute per connection
- Webhook creation: 10 per minute per IP
