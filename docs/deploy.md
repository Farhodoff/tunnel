# Deploy

Production target is a VPS (not serverless — tunnels need long-lived
WebSockets, connection state and raw TCP ports).

```bash
DOMAIN=tunnel.example.com EMAIL=you@example.com bash deploy/install.sh
```

Wildcard TLS (`*.DOMAIN`) requires a DNS-01 certificate:

```bash
sudo certbot certonly --manual --preferred-challenges dns \
  -d tunnel.example.com -d '*.tunnel.example.com'
```

See `deploy/nginx.conf` (template), `deploy/tunnel.service` (systemd),
`deploy/install.sh` (full installer) and `README.md`.
