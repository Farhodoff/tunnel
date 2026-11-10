# 🚀 Tunelio Production Deployment & Hardening Guide

## Requirements
- Linux VPS (Ubuntu 22.04 LTS / Debian 12)
- Docker & Docker Compose
- Wildcard DNS Record: `*.tunnel.yourdomain.com -> VPS_IP`

## Step-by-Step Setup
1. **Clone repository:**
   ```bash
   git clone https://github.com/Farhodoff/tunnel.git /opt/tunnel
   cd /opt/tunnel
   ```
2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Set TUNNEL_HOST, REDIS_URL, and AUTH_ENABLED=true
   ```
3. **Launch Production Stack:**
   ```bash
   docker compose -f deploy/docker-compose.prod.yml up -d
   ```
4. **Verify Health:**
   ```bash
   curl -f http://localhost/health
   ```
