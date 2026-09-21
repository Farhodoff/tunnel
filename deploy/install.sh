#!/usr/bin/env bash
# Tunnel VPS installer (Ubuntu 22.04+)
# Usage:
#   DOMAIN=tunnel.example.com EMAIL=you@example.com bash deploy/install.sh
#   # with Redis:
#   DOMAIN=tunnel.example.com EMAIL=you@example.com WITH_REDIS=1 bash deploy/install.sh
#
# What it does:
#   1. Installs docker, nginx, certbot, ufw
#   2. Creates /opt/tunnel/.env from .env.example (edits DOMAIN)
#   3. Opens firewall (80/443 + optional TCP_RANGE), starts stack
#   4. Installs nginx vhost from deploy/nginx.conf (envsubst)
#   5. Wildcard cert MUST be DNS-01 (script prints the command, does not fake it)
set -euo pipefail

DOMAIN="${DOMAIN:?set DOMAIN=tunnel.example.com}"
EMAIL="${EMAIL:?set EMAIL=you@example.com}"
WITH_REDIS="${WITH_REDIS:-0}"
TCP_RANGE="${TCP_RANGE:-19000:19100}"   # exposed only if you use --tcp
APP_DIR="/opt/tunnel"

echo "==> [1/6] system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq docker.io docker-compose-plugin nginx certbot python3-certbot-nginx gettext ufw > /dev/null

echo "==> [2/6] app dir + env"
sudo mkdir -p "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  # fresh VPS: clone (expects access to the repo)
  sudo git clone https://github.com/Farhodoff/tunnel.git "$APP_DIR-tmp" 2>/dev/null || true
  if [ -d "$APP_DIR-tmp" ]; then
    sudo cp -r "$APP_DIR-tmp"/. "$APP_DIR"/
    sudo rm -rf "$APP_DIR-tmp"
  fi
fi
if [ ! -f "$APP_DIR/.env" ]; then
  sudo cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  sudo sed -i "s/^TUNNEL_DOMAIN=.*/TUNNEL_DOMAIN=$DOMAIN/" "$APP_DIR/.env"
  echo "!! EDIT $APP_DIR/.env : set TUNNEL_API_KEYS (required for prod)"
fi
sudo mkdir -p "$APP_DIR/certs"

echo "==> [3/6] firewall"
sudo ufw allow 22/tcp >/dev/null 2>&1 || true
sudo ufw allow 80/tcp >/dev/null 2>&1 || true
sudo ufw allow 443/tcp >/dev/null 2>&1 || true
if [ -n "$TCP_RANGE" ]; then
  # shellcheck disable=SC2086
  sudo ufw allow $TCP_RANGE/tcp >/dev/null 2>&1 || true
fi
sudo ufw --force enable >/dev/null 2>&1 || true

echo "==> [4/6] docker stack"
cd "$APP_DIR"
if [ "$WITH_REDIS" = "1" ]; then
  export TUNNEL_REDIS_URL="redis://redis:6379/0"
  sudo docker compose --profile with-redis up -d --build
else
  sudo docker compose up -d --build
fi
sleep 5
curl -f http://localhost:8080/health || { echo "server not healthy"; sudo docker compose logs --tail=30; exit 1; }

echo "==> [5/6] nginx vhost"
export DOMAIN
envsubst '$DOMAIN' < "$APP_DIR/deploy/nginx.conf" | sudo tee /etc/nginx/sites-enabled/tunnel.conf > /dev/null
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo "==> [6/6] TLS (wildcard needs DNS-01!)"
echo "Apex HTTP-01 (optional, only covers $DOMAIN itself):"
echo "  sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL"
echo "Wildcard for tunnels (REQUIRED for *.${DOMAIN}, DNS-01):"
echo "  sudo certbot certonly --manual --preferred-challenges dns \\"
echo "    -d $DOMAIN -d '*.$DOMAIN' -m $EMAIL --agree-tos"
echo "Then: sudo nginx -t && sudo systemctl reload nginx"
echo
echo "DONE. Health: curl http://localhost:8080/health"
echo "Dashboard: https://$DOMAIN/dashboard (after cert)"
echo "Client: python -m tunnel.cli client --server wss://$DOMAIN --port 3000 --subdomain myapp"
