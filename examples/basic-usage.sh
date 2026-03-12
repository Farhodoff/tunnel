#!/bin/bash
# Basic usage examples for Tunnel

# ============ SERVER ============

# 1. Development server
python3 -m tunnel.cli server --port 8080

# 2. Production server with SSL
python3 -m tunnel.cli server \
  --port 8443 \
  --ssl-cert /path/to/cert.pem \
  --ssl-key /path/to/key.pem

# 3. Server with environment variables
export TUNNEL_DOMAIN=tunnel.example.com
export TUNNEL_API_KEYS="key1,key2"
python3 -m tunnel.cli server

# ============ CLIENT ============

# 1. Basic client
python3 -m tunnel.cli client \
  --server ws://localhost:8080 \
  --port 3000

# 2. Client with custom subdomain
python3 -m tunnel.cli client \
  --server wss://tunnel.example.com \
  --port 3000 \
  --subdomain myapp \
  --token your_api_key

# 3. Client with HTTPS server
python3 -m tunnel.cli client \
  --server wss://tunnel.example.com \
  --port 8080

# ============ DOCKER ============

# 1. Build and run
docker build -t tunnel-server .
docker run -p 8080:8080 -e TUNNEL_API_KEYS=key1 tunnel-server

# 2. Docker Compose
docker-compose up -d

# ============ TESTING ============

# Test HTTP tunnel
curl -H "host: myapp.tunnel.dev" http://localhost:8080/

# Test HTTPS tunnel (skip SSL verification)
curl -k -H "host: myapp.tunnel.dev" https://localhost:8443/

# View dashboard
open http://localhost:8080/dashboard

# View metrics
curl http://localhost:8080/metrics
