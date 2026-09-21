"""
FastAPI Server Application
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import JSONResponse

from tunnel.core.protocol import (
    Message, MessageType, create_connect_ack, create_error, ErrorCode
)
from tunnel.server.connection import ConnectionManager
from tunnel.server.dashboard import router as dashboard_router
from tunnel.server.webhook_tester import router as webhook_router
from tunnel.auth.routes import router as auth_router
from tunnel.server.tcp_handler import TCPHandler
from tunnel.auth.manager import auth_manager
from tunnel.utils.rate_limiter import rate_limiter
from tunnel.utils.request_logger import request_logger
from tunnel.utils.metrics import metrics


# Global connection manager
import os as _os
manager = ConnectionManager(
    base_domain=_os.getenv("TUNNEL_DOMAIN", "tunnel.dev"),
    use_https=bool(_os.getenv("TUNNEL_SSL_CERT") and _os.getenv("TUNNEL_SSL_KEY")),
)

# Global TCP handler
tcp_handler = TCPHandler(manager)

# Load auth keys: file first (persisted), then environment
auth_manager.configure_from_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    rate_limiter.configure_from_env()
    auth_manager.configure_from_env()
    print(f"[Server] Starting up... rate_limit={rate_limiter.max_requests}/{rate_limiter.window_seconds}s backend={rate_limiter.backend} auth={'enabled' if auth_manager.is_enabled else 'disabled'}")

    async def _stale_sweeper():
        while True:
            try:
                await asyncio.sleep(60)
                await manager.cleanup_stale(max_idle=300)
                rate_limiter.cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Server] sweeper error: {e}")

    sweeper = asyncio.create_task(_stale_sweeper())
    try:
        yield
    finally:
        sweeper.cancel()
        print("[Server] Shutting down...")


app = FastAPI(
    title="Tunnel Server",
    description="Secure tunnel service",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(dashboard_router)
app.include_router(webhook_router)
app.include_router(auth_router)


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    stats = await manager.get_stats()
    metrics.set_active_tunnels(stats.get("active_tunnels", 0))
    return Response(
        content=metrics.to_prometheus_format(),
        media_type="text/plain"
    )


@app.get("/api/logs")
async def get_logs(limit: int = 100, subdomain: Optional[str] = None):
    """Get request logs"""
    return {
        "logs": request_logger.get_entries(limit, subdomain),
        "stats": request_logger.get_stats()
    }


@app.get("/")
async def root():
    return {"service": "Tunnel Server", "version": "1.0.0"}


@app.get("/health")
async def health():
    stats = await manager.get_stats()
    return {"status": "healthy", "tunnels": stats}


@app.get("/api/tunnels")
async def list_tunnels():
    stats = await manager.get_stats()
    stats["base_domain"] = manager.base_domain
    stats["use_https"] = manager.use_https
    return stats


@app.websocket("/tunnel")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for tunnel connections"""
    await websocket.accept()
    
    tunnel = None
    
    try:
        # Wait for connect message
        data = await websocket.receive_text()
        message = Message.from_json(data)
        
        if message.msg_type != MessageType.CONNECT.value:
            error = create_error(ErrorCode.INVALID_MESSAGE, "First message must be CONNECT")
            await websocket.send_text(error.to_json())
            await websocket.close()
            return
        
        # Extract connection info
        payload = message.payload
        subdomain = payload.get("subdomain")
        local_port = payload.get("local_port", 3000)
        auth_token = payload.get("auth_token")
        tcp_enabled = bool(payload.get("tcp_enabled", False))
        tcp_public_port = int(payload.get("tcp_public_port") or 0)
        tcp_target_host = payload.get("tcp_target_host") or "127.0.0.1"
        tcp_target_port = payload.get("tcp_target_port") or local_port
        
        # Validate auth token
        if auth_manager.is_enabled:
            if not auth_manager.validate_key(auth_token):
                error = create_error(ErrorCode.AUTH_FAILED, "Invalid or missing API key")
                await websocket.send_text(error.to_json())
                await websocket.close()
                return
        
        # Validate subdomain before creating tunnel
        from tunnel.server.connection import validate_subdomain
        _ok, _reason = validate_subdomain(subdomain)
        if not _ok:
            error = create_error(ErrorCode.INVALID_MESSAGE, _reason)
            await websocket.send_text(error.to_json())
            await websocket.close()
            return

        # Validate TCP port if requested
        if tcp_enabled:
            if tcp_public_port < 0 or tcp_public_port > 65535:
                error = create_error(ErrorCode.INVALID_MESSAGE, "Invalid tcp_public_port (0-65535)")
                await websocket.send_text(error.to_json())
                await websocket.close()
                return
            if tcp_public_port and tcp_handler.is_port_in_use(tcp_public_port):
                error = create_error(ErrorCode.SUBDOMAIN_TAKEN, f"TCP port {tcp_public_port} is taken")
                await websocket.send_text(error.to_json())
                await websocket.close()
                return

        # Create tunnel
        tunnel = await manager.create_tunnel(
            websocket, local_port, subdomain,
            tcp_enabled=tcp_enabled,
            tcp_public_port=tcp_public_port,
            tcp_target_host=tcp_target_host,
            tcp_target_port=tcp_target_port,
        )
        
        if not tunnel:
            error = create_error(ErrorCode.SUBDOMAIN_TAKEN, f"Subdomain '{subdomain}' is taken")
            await websocket.send_text(error.to_json())
            await websocket.close()
            return

        # Start TCP listener if requested
        tcp_port_actual: Optional[int] = None
        if tcp_enabled:
            try:
                await tcp_handler.start_tcp_listener(
                    tcp_public_port, tunnel.tunnel_id,
                    tcp_target_host, tcp_target_port,
                )
                tcp_port_actual = tcp_handler.get_listener_port(tunnel.tunnel_id)
                tunnel.tcp_public_port = tcp_port_actual
            except OSError as e:
                await manager.remove_tunnel(tunnel.tunnel_id)
                error = create_error(ErrorCode.INTERNAL_ERROR, f"TCP listen failed: {e}")
                await websocket.send_text(error.to_json())
                await websocket.close()
                return
        
        # Send acknowledgment
        tcp_public_url = f"tcp://{manager.base_domain}:{tcp_port_actual}" if tcp_port_actual else None
        ack = create_connect_ack(
            tunnel_id=tunnel.tunnel_id,
            subdomain=tunnel.subdomain,
            public_url=manager.get_public_url(tunnel.subdomain),
            tcp_port=tcp_port_actual,
            tcp_public_url=tcp_public_url,
        )
        await websocket.send_text(ack.to_json())
        
        print(f"[Server] Tunnel created: {tunnel.subdomain} -> localhost:{local_port}")
        
        # Main message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = Message.from_json(data)
                
                if message.msg_type == MessageType.HTTP_RESPONSE.value:
                    await manager.handle_response(tunnel.tunnel_id, message.payload)
                
                elif message.msg_type == MessageType.TCP_DATA.value:
                    await tcp_handler.handle_tcp_data(tunnel.tunnel_id, message.payload)
                
                elif message.msg_type == MessageType.TCP_CLOSE.value:
                    await tcp_handler.handle_tcp_close(tunnel.tunnel_id, message.payload)
                
                elif message.msg_type == MessageType.PONG.value:
                    tunnel.touch()
                
                elif message.msg_type == MessageType.DISCONNECT.value:
                    break
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[Server] Message error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Server] WebSocket error: {e}")
    finally:
        if tunnel:
            await tcp_handler.stop_tcp_listener(tunnel.tunnel_id)
            await manager.remove_tunnel(tunnel.tunnel_id)
            print(f"[Server] Tunnel closed: {tunnel.subdomain}")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_request(request: Request, path: str):
    """Proxy HTTP requests to tunnels"""
    
    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "retry_after": int(rate_limiter.get_reset_time(client_ip) - __import__('time').time())
            }
        )
    
    # Extract subdomain from host
    host = request.headers.get("host", "")
    subdomain = None
    
    if "." in host:
        parts = host.split(".")
        if len(parts) >= 2:
            subdomain = parts[0]
    
    if not subdomain:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid host header"}
        )
    
    # Get tunnel
    tunnel = await manager.get_by_subdomain(subdomain)
    if not tunnel:
        return JSONResponse(
            status_code=404,
            content={"error": f"Tunnel not found: {subdomain}"}
        )
    
    # Build request
    method = request.method
    headers = dict(request.headers)

    # Read raw body (binary-safe -> base64 for WS transport)
    import base64 as _b64
    body = None
    body_b64 = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            body_b64 = _b64.b64encode(body_bytes).decode()
            try:
                body = body_bytes.decode("utf-8")
            except UnicodeDecodeError:
                body = None  # binary only, client must use body_b64
    except Exception:
        pass

    # Build path with query string (preserve raw query)
    raw_query = request.url.query
    full_path = f"/{path}"
    if raw_query:
        full_path += f"?{raw_query}"

    # Forward request
    start_time = time.time()
    response_data = await manager.forward_request(
        subdomain=subdomain,
        method=method,
        path=full_path,
        headers=headers,
        body=body,
        body_b64=body_b64,
    )
    duration_ms = (time.time() - start_time) * 1000
    
    if response_data is None:
        # Log failed request
        request_logger.log(method, full_path, subdomain, client_ip, 502, duration_ms)
        metrics.record_request(method, 502, duration_ms)
        return JSONResponse(
            status_code=502,
            content={"error": "Failed to forward request"}
        )
    
    status_code = response_data.get("status_code", 502)
    
    # Log request
    request_logger.log(method, full_path, subdomain, client_ip, status_code, duration_ms)
    metrics.record_request(method, status_code, duration_ms)
    
    # Decode body (prefer binary-safe body_b64, fallback to legacy body)
    import base64 as _b64dec
    content: bytes = b""
    if response_data.get("body_b64"):
        try:
            content = _b64dec.b64decode(response_data["body_b64"])
        except Exception:
            content = (response_data.get("body") or "").encode()
    else:
        content = (response_data.get("body") or "").encode()

    # Preserve upstream headers except hop-by-hop; let Starlette set content-length
    _hop_resp = {"content-length", "connection", "transfer-encoding",
                 "keep-alive", "proxy-authenticate", "proxy-authorization",
                 "te", "trailer", "upgrade"}
    resp_headers = {k: v for k, v in (response_data.get("headers") or {}).items()
                    if k.lower() not in _hop_resp}
    # Ensure content-type always present (case-insensitive check)
    if not any(k.lower() == "content-type" for k in resp_headers):
        resp_headers["content-type"] = "application/octet-stream"

    return Response(
        content=content,
        status_code=status_code,
        headers=resp_headers,
    )
