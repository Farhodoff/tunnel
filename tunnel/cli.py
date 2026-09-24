"""
CLI - Command line interface for tunnel
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from tunnel.server.app import app as server_app, manager as connection_manager
from tunnel.client.tunnel_client import TunnelClient


def run_server():
    """Run tunnel server"""
    import os

    parser = argparse.ArgumentParser(description="Tunnel Server")
    # nosec B104 --host 0.0.0.0 is intentional: public tunnel server
    parser.add_argument(
        "--host",
        default=os.getenv("TUNNEL_HOST", "0.0.0.0"),  # nosec
        help="Host to bind",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("TUNNEL_PORT", "8080")),
        help="Port to bind",
    )
    parser.add_argument(
        "--domain", default=os.getenv("TUNNEL_DOMAIN", "tunnel.dev"), help="Base domain"
    )
    parser.add_argument(
        "--ssl-cert", default=os.getenv("TUNNEL_SSL_CERT"), help="SSL certificate file"
    )
    parser.add_argument(
        "--ssl-key", default=os.getenv("TUNNEL_SSL_KEY"), help="SSL key file"
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=int(os.getenv("TUNNEL_RATE_LIMIT", "100")),
        help="HTTP requests per minute per IP",
    )
    parser.add_argument(
        "--rate-window",
        type=int,
        default=int(os.getenv("TUNNEL_RATE_WINDOW", "60")),
        help="Rate limit window in seconds",
    )
    parser.add_argument(
        "--redis-url",
        default=os.getenv("TUNNEL_REDIS_URL", ""),
        help="Redis URL for distributed rate limiting (empty=memory)",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("Tunnel Server")
    print("=" * 50)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Domain: {args.domain}")
    print(
        f"Rate: {args.rate_limit}/{args.rate_window}s backend={'redis' if args.redis_url else 'memory'}"
    )

    # Apply domain + scheme to shared manager BEFORE uvicorn starts
    connection_manager.set_base_domain(args.domain)
    from tunnel.utils.rate_limiter import rate_limiter as _rl

    _rl.configure(
        max_requests=args.rate_limit,
        window_seconds=args.rate_window,
        redis_url=args.redis_url or None,
    )
    # SSL configuration
    ssl_cert = args.ssl_cert or "certs/server.crt"
    ssl_key = args.ssl_key or "certs/server.key"

    import os

    ssl_enabled = bool(
        ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key)
    )
    connection_manager.set_use_https(ssl_enabled)
    if ssl_enabled:
        print(f"SSL: Enabled (cert: {ssl_cert})")
        print(f"WebSocket: wss://{args.host}:{args.port}/tunnel")
        print(f"Dashboard: https://{args.host}:{args.port}/dashboard")
        print("=" * 50)

        uvicorn.run(
            server_app,
            host=args.host,
            port=args.port,
            ssl_certfile=ssl_cert,
            ssl_keyfile=ssl_key,
        )
    else:
        print(f"SSL: Disabled (cert not found)")
        print(f"WebSocket: ws://{args.host}:{args.port}/tunnel")
        print(f"Dashboard: http://{args.host}:{args.port}/dashboard")
        print("=" * 50)

        uvicorn.run(server_app, host=args.host, port=args.port)


def _load_client_config(path: Optional[str]) -> dict:
    """Load client JSON config (see examples/client-config.json). Missing file -> {}."""
    import json
    import os

    if not path:
        return {}
    try:
        with open(os.path.expanduser(path)) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        print(f"[Client] Config not found: {path}")
        return {}
    except Exception as e:
        print(f"[Client] Bad config {path}: {e}")
        return {}


def run_client():
    """Run tunnel client"""
    import os

    parser = argparse.ArgumentParser(description="Tunnel Client")
    parser.add_argument(
        "--server",
        "-s",
        default=None,
        help="Server URL (env TUNNEL_SERVER, default: ws://localhost:8080)",
    )
    parser.add_argument(
        "--port", "-p", type=int, default=None, help="Local server port (default: 3000)"
    )
    parser.add_argument("--subdomain", default=None, help="Custom subdomain")
    parser.add_argument("--token", default=None, help="Auth token (env TUNNEL_TOKEN)")
    parser.add_argument("--tcp", action="store_true", help="Enable TCP forwarding")
    parser.add_argument(
        "--tcp-port", type=int, default=None, help="Public TCP port on server (0=auto)"
    )
    parser.add_argument(
        "--tcp-target-host", default=None, help="Local TCP host to forward to"
    )
    parser.add_argument(
        "--tcp-target-port",
        type=int,
        default=None,
        help="Local TCP port to forward to (default: --port)",
    )
    parser.add_argument(
        "--local-host", default=None, help="Local HTTP host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--local-https", action="store_true", help="Use https:// for local server"
    )
    parser.add_argument(
        "--insecure", action="store_true", help="Skip TLS verify for local https"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Max connect attempts, 0=infinite (default)",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=os.getenv("TUNNEL_CONFIG", ""),
        help="JSON config file (see examples/client-config.json)",
    )

    args = parser.parse_args()
    cfg = _load_client_config(args.config)
    rec = cfg.get("reconnect", {}) if isinstance(cfg.get("reconnect"), dict) else {}

    def pick(name, *fallbacks):
        v = getattr(args, name, None)
        if v not in (None, "", False) or name in ("tcp", "local_https", "insecure"):
            # flags: CLI True wins, else config
            if isinstance(v, bool):
                return v or bool(cfg.get(name, False))
            if v is not None:
                return v
        for fb in fallbacks:
            if fb not in (None, ""):
                return fb
        return None

    server = pick(
        "server", cfg.get("server"), os.getenv("TUNNEL_SERVER"), "ws://localhost:8080"
    )
    port = pick("port", cfg.get("port", cfg.get("local_port")), 3000)
    subdomain = pick("subdomain", cfg.get("subdomain"))
    token = pick(
        "token", cfg.get("token", cfg.get("auth_token")), os.getenv("TUNNEL_TOKEN")
    )
    tcp_port = pick("tcp_port", cfg.get("tcp_port"), 0)
    tcp_target_host = pick("tcp_target_host", cfg.get("tcp_target_host"), "127.0.0.1")
    tcp_target_port = pick("tcp_target_port", cfg.get("tcp_target_port"), port)
    local_host = pick("local_host", cfg.get("local_host"), "127.0.0.1")
    max_retries = pick("max_retries", rec.get("max_attempts"), 0)

    print("=" * 50)
    print("Tunnel Client")
    print("=" * 50)
    print(f"Server: {server}")
    print(
        f"Local: {'https' if (args.local_https or cfg.get('local_https')) else 'http'}://{local_host}:{port}"
    )
    if subdomain:
        print(f"Requested subdomain: {subdomain}")
    if args.tcp or cfg.get("tcp"):
        print(
            f"TCP: enabled (public={tcp_port or 'auto'} -> {tcp_target_host}:{tcp_target_port})"
        )
    print("=" * 50)

    client = TunnelClient(
        server_url=server,
        local_port=port,
        subdomain=subdomain,
        auth_token=token,
        tcp_enabled=bool(args.tcp or cfg.get("tcp")),
        tcp_public_port=tcp_port or 0,
        tcp_target_host=tcp_target_host,
        tcp_target_port=tcp_target_port,
        local_host=local_host,
        local_https=bool(args.local_https or cfg.get("local_https")),
        insecure=bool(args.insecure or cfg.get("insecure")),
        max_retries=max_retries or 0,
    )

    try:
        code = asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n[Client] Exiting...")
        code = 0
    sys.exit(code if isinstance(code, int) else 0)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m tunnel.cli [server|client] [options]")
        sys.exit(1)

    command = sys.argv[1]
    # Remove command from args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "server":
        run_server()
    elif command == "client":
        run_client()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python -m tunnel.cli [server|client] [options]")
        sys.exit(1)


if __name__ == "__main__":
    main()
