"""
CLI - Command line interface for tunnel
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from tunnel.server.app import app as server_app
from tunnel.client.tunnel_client import TunnelClient


def run_server():
    """Run tunnel server"""
    parser = argparse.ArgumentParser(description="Tunnel Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    parser.add_argument("--domain", default="tunnel.dev", help="Base domain")
    parser.add_argument("--ssl-cert", help="SSL certificate file")
    parser.add_argument("--ssl-key", help="SSL key file")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Tunnel Server")
    print("=" * 50)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Domain: {args.domain}")
    
    # SSL configuration
    ssl_cert = args.ssl_cert or "certs/server.crt"
    ssl_key = args.ssl_key or "certs/server.key"
    
    import os
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print(f"SSL: Enabled (cert: {ssl_cert})")
        print(f"WebSocket: wss://{args.host}:{args.port}/tunnel")
        print(f"Dashboard: https://{args.host}:{args.port}/dashboard")
        print("=" * 50)
        
        uvicorn.run(
            server_app, 
            host=args.host, 
            port=args.port,
            ssl_certfile=ssl_cert,
            ssl_keyfile=ssl_key
        )
    else:
        print(f"SSL: Disabled (cert not found)")
        print(f"WebSocket: ws://{args.host}:{args.port}/tunnel")
        print(f"Dashboard: http://{args.host}:{args.port}/dashboard")
        print("=" * 50)
        
        uvicorn.run(server_app, host=args.host, port=args.port)


def run_client():
    """Run tunnel client"""
    parser = argparse.ArgumentParser(description="Tunnel Client")
    parser.add_argument("--server", "-s", default="ws://localhost:8080",
                       help="Server URL (default: ws://localhost:8080)")
    parser.add_argument("--port", "-p", type=int, default=3000,
                       help="Local server port (default: 3000)")
    parser.add_argument("--subdomain", help="Custom subdomain")
    parser.add_argument("--token", help="Auth token")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Tunnel Client")
    print("=" * 50)
    print(f"Server: {args.server}")
    print(f"Local port: {args.port}")
    if args.subdomain:
        print(f"Requested subdomain: {args.subdomain}")
    print("=" * 50)
    
    client = TunnelClient(
        server_url=args.server,
        local_port=args.port,
        subdomain=args.subdomain,
        auth_token=args.token
    )
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n[Client] Exiting...")


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
