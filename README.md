# Tunnel - ngrok-like Tunnel Service

A secure, scalable tunnel service built with Python, FastAPI, and WebSocket.

## Features

- **HTTP/HTTPS Tunneling** - Expose local HTTP servers to the internet
- **TCP Tunneling** - Raw TCP tunneling for SSH, MySQL, Redis, etc.
- **WebSocket Support** - Real-time bidirectional communication
- **Authentication** - API key-based authentication
- **Dashboard** - Web UI for monitoring tunnels
- **Rate Limiting** - Prevent abuse with configurable limits
- **Request Logging** - Track all requests for debugging
- **Metrics** - Prometheus-compatible metrics
- **Webhook Testing** - Test and debug webhooks
- **Docker Support** - Easy deployment with Docker

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/tunnel.git
cd tunnel

# Install dependencies
pip install -r requirements.txt
```

### Run Server

```bash
# Development
python -m tunnel.cli server --port 8080

# Production with SSL
python -m tunnel.cli server --port 8443 --ssl-cert certs/server.crt --ssl-key certs/server.key
```

### Run Client

```bash
# Expose local server on port 3000
python -m tunnel.cli client --server ws://localhost:8080 --port 3000

# With custom subdomain
python -m tunnel.cli client --server ws://localhost:8080 --port 3000 --subdomain myapp
```

## Docker Deployment

```bash
# Build image
docker build -t tunnel-server .

# Run container
docker run -p 8080:8080 -e TUNNEL_API_KEYS=your_key tunnel-server

# Or use docker-compose
docker-compose up -d
```

## Production Deployment

### Prerequisites

- Ubuntu 20.04+ server
- Domain name (e.g., `tunnel.example.com`)
- DNS A record: `*.tunnel.example.com` pointing to server IP

### Step-by-Step Guide

1. **Install dependencies**
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nginx certbot
```

2. **Setup application**
```bash
sudo mkdir -p /opt/tunnel
sudo cp -r . /opt/tunnel/
cd /opt/tunnel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure environment**
```bash
sudo cp .env.example .env
sudo nano .env  # Edit configuration
```

4. **Setup SSL certificates**
```bash
sudo certbot certonly --standalone -d tunnel.example.com -d *.tunnel.example.com
```

5. **Configure Nginx**
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/tunnel
sudo ln -s /etc/nginx/sites-available/tunnel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

6. **Setup systemd service**
```bash
sudo cp deploy/tunnel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tunnel
sudo systemctl start tunnel
```

## API Endpoints

### Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server info |
| `/health` | GET | Health check |
| `/dashboard` | GET | Web UI |
| `/metrics` | GET | Prometheus metrics |
| `/api/tunnels` | GET | List active tunnels |
| `/api/logs` | GET | Request logs |
| `/tunnel` | WS | WebSocket endpoint |

### Webhook Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/create` | POST | Create webhook endpoint |
| `/webhooks/capture/{id}` | ALL | Capture webhook |
| `/webhooks/requests/{id}` | GET | Get captured requests |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TUNNEL_DOMAIN` | Base domain | `tunnel.dev` |
| `TUNNEL_PORT` | Server port | `8080` |
| `TUNNEL_API_KEYS` | Comma-separated API keys | - |
| `TUNNEL_SSL_CERT` | SSL certificate path | - |
| `TUNNEL_SSL_KEY` | SSL key path | - |
| `TUNNEL_RATE_LIMIT` | Requests per minute | `100` |

## Architecture

```
Internet User
     ↓
Public URL (subdomain.tunnel.dev)
     ↓
Nginx (SSL termination)
     ↓
Tunnel Server (FastAPI)
     ↓
WebSocket Connection
     ↓
Tunnel Client (local machine)
     ↓
Local Server (localhost:port)
```

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest

# Format code
black tunnel/
```

## License

MIT License
# tunnel
