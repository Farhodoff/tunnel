# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Performance monitoring with latency and bandwidth graphs
- Custom domain support
- CLI directory structure for better organization
- GitHub Actions CI/CD workflow

### Completed
- Added `POST /api/logs/{request_id}/replay` for replaying captured requests
- Added recent request inspection and replay controls to the dashboard
- Added filtered latency/status/bandwidth metrics to the dashboard
- Added exact custom-domain routing via `TUNNEL_CUSTOM_DOMAINS`

## [1.0.0] - 2024-01-XX

### Added
- Initial release of Tunnel service
- HTTP/HTTPS tunneling support
- WebSocket protocol for real-time communication
- TCP tunneling for SSH, databases, etc.
- API key authentication system
- Web dashboard for monitoring
- Rate limiting and bandwidth control
- Request logging and metrics (Prometheus)
- Webhook testing endpoints
- Docker and Docker Compose support
- SSL/HTTPS support with self-signed certificates
- Nginx reverse proxy configuration
- Systemd service file
- Comprehensive test suite (pytest)
- Examples and documentation

### Features
- **Core**: FastAPI-based server with WebSocket support
- **Protocol**: JSON-based message protocol for tunnel communication
- **Client**: CLI client for connecting to tunnel server
- **Security**: API key authentication and SSL support
- **Observability**: Dashboard, metrics, and logging
- **Deployment**: Docker, docker-compose, and systemd support
