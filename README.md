## 🛠 Technologies

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-005863?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Uvicorn-202324?style=for-the-badge&logo=uvicorn&logoColor=white" alt="Uvicorn" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white" alt="Prometheus" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white" alt="GitHub Actions" />
  <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
</p>

<p align="center">
  <b>WebSockets</b> • <b>aiohttp</b> • <b>MkDocs</b> • <b>Cryptography (SSL/TLS)</b>
</p>

---

# Tunelio (Tunnel)

Tunelio is a robust, Python-based tunneling application that exposes your local web servers to the internet. Built with FastAPI and WebSockets, it serves as a lightweight alternative to tools like ngrok or localtunnel, enabling seamless development, webhook testing, and secure remote access.

## Features

- **HTTP/HTTPS Tunneling**: Expose any local port to a public subdomain.
- **WebSocket Protocol**: Fast and persistent connection between the client and server.
- **Custom Subdomains**: Request specific subdomains for your tunnels.
- **Dashboard & Analytics**: Built-in web dashboard to monitor active tunnels, requests, and metrics.
- **Authentication**: Secure your tunnel server with API tokens.
- **Docker Support**: Easy deployment using Docker and Docker Compose.
- **SSL Support**: Built-in capabilities to handle SSL certificates.
- **Monitoring**: Integration with Prometheus for metrics and health monitoring.

---



## Installation

### Prerequisites
- Python 3.8+
- (Optional) Docker and Docker Compose

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Farhodoff/tunnel.git
   cd tunnel
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

---

## Usage

The application provides a single CLI entry point for both the server and the client.

### 1. Running the Server

Start the tunnel server on a reachable machine or locally for testing.

```bash
python -m tunnel.cli server --host 0.0.0.0 --port 8080 --domain tunnel.dev
```

**Server Options:**
- `--host`: Host to bind (default: `0.0.0.0`)
- `--port`: Port to listen on (default: `8080`)
- `--domain`: Base domain for the tunnels (default: `tunnel.dev`)
- `--ssl-cert`: Path to SSL certificate (default: `certs/server.crt`)
- `--ssl-key`: Path to SSL key (default: `certs/server.key`)

*Note: If valid SSL certificates are provided, the server will enable WSS and HTTPS. Otherwise, it defaults to WS and HTTP.*

### 2. Running the Client

Start the client to expose your local application. For example, to expose a local web server running on port `3000`:

```bash
python -m tunnel.cli client --server ws://localhost:8080 --port 3000 --subdomain myapp
```

**Client Options:**
- `--server`, `-s`: Server WebSocket URL (default: `ws://localhost:8080`)
- `--port`, `-p`: Local port you want to expose (default: `3000`)
- `--subdomain`: Request a specific custom subdomain
- `--token`: Authentication token (if required by the server)

### 3. Accessing the Services

- **Dashboard**: `http://localhost:8080/dashboard` (or `https://` if SSL is enabled)
- **Public URL**: `http://myapp.tunnel.dev` (Routes traffic to your local port `3000`)
- **WebSocket Endpoint**: `ws://localhost:8080/tunnel`

---

## Docker Deployment

You can quickly deploy the tunnel server using Docker Compose.

1. Configure your environment variables in a `.env` file (see `.env.example`).
2. Run the server:
   ```bash
   docker-compose up -d
   ```

This will run the tunnel server on port `8080`. Redis can optionally be enabled by using the `with-redis` profile to support distributed rate limiting.

---

## Architecture & API

- **API Documentation**: Detailed information about the WebSocket protocol and REST API endpoints can be found in `API.md`.
- **Metrics**: Prometheus-formatted metrics are exposed at `/metrics`.
- **Health Check**: Available at `/health`.

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
**Error:** `[Errno 48] Address already in use`

**Solution:**
```bash
# Find process using the port
lsof -i :8080
# or
netstat -tulpn | grep 8080

# Kill the process
kill -9 <PID>

# Or use a different port
python -m tunnel.cli server --port 8888
```

#### 2. DNS Resolution Failed
**Error:** `DNS_PROBE_FINISHED_NXDOMAIN`

**Solution:**
For local testing, add to `/etc/hosts`:
```bash
127.0.0.1 testapp.tunnel.dev
127.0.0.1 myapp.tunnel.dev
```

Or use `curl` with Host header:
```bash
curl -H "Host: myapp.tunnel.dev" http://localhost:8080/
```

#### 3. SSL Certificate Errors
**Error:** `SSL certificate verify failed`

**Solution:**
For self-signed certificates, use `-k` flag with curl:
```bash
curl -k https://localhost:8443/
```

Or install the certificate:
```bash
# macOS
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/server.crt

# Linux
sudo cp certs/server.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

#### 4. WebSocket Connection Failed
**Error:** `WebSocket connection failed`

**Solution:**
- Check if server is running: `curl http://localhost:8080/health`
- Verify firewall settings
- Check WebSocket URL protocol (ws:// vs wss://)

#### 5. Authentication Failed
**Error:** `Invalid or missing API key`

**Solution:**
```bash
# Generate API key
python -c "from tunnel.auth.manager import auth_manager; print(auth_manager.generate_key('My Key'))"

# Use with client
python -m tunnel.cli client --server ws://localhost:8080 --port 3000 --token YOUR_KEY
```

### Debug Mode

Enable debug logging:
```bash
export TUNNEL_LOG_LEVEL=DEBUG
python -m tunnel.cli server --port 8080
```

### Getting Help

- Check logs: `tail -f /var/log/tunnel/server.log`
- Run tests: `pytest tests/ -v`
- View examples: `examples/`

---

## Examples

See the `examples/` directory for:
- `client-config.json` - Client configuration
- `server-config.json` - Server configuration
- `basic-usage.sh` - Common commands
- `api-examples.py` - Python API usage

---

## License

MIT License
