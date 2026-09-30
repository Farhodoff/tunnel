# Tunelio

Tunelio exposes your local web servers to the internet over persistent
WebSockets — a lightweight ngrok alternative built with FastAPI.

- Quickstart: see `README.md` (Usage + Docker sections)
- Production VPS: `deploy/` + `README.md` ("Production Deployment")
- Full protocol + REST reference: `API.md`

## Endpoints

| Path | Purpose |
|------|---------|
| `/tunnel` | WebSocket endpoint for clients |
| `/dashboard` | Web UI for active tunnels |
| `/health` | Health check |
| `/metrics` | Prometheus metrics |
| `/api/tunnels` | List tunnels |
| `/api/keys` | API key management (persisted) |
| `/api/logs` | Request logs |
| `/webhooks/*` | Webhook capture + testing |

## Client cheat-sheet

```bash
# HTTP tunnel
python -m tunnel.cli client -s wss://tunnel.example.com -p 3000 --subdomain myapp --token tun_...

# TCP forward (local :22 on server :19000)
python -m tunnel.cli client -s wss://tunnel.example.com -p 3000 --tcp --tcp-port 19000 --tcp-target-port 22

# From config file
python -m tunnel.cli client --config examples/client-config.json
```
