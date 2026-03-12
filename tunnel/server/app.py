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
from tunnel.server.tcp_handler import TCPHandler
from tunnel.auth.manager import auth_manager
from tunnel.utils.rate_limiter import rate_limiter
from tunnel.utils.request_logger import request_logger
from tunnel.utils.metrics import metrics


# Global connection manager
manager = ConnectionManager()

# Global TCP handler
tcp_handler = TCPHandler(manager)

# Load auth keys from environment
auth_manager.load_keys_from_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    print("[Server] Starting up...")
    yield
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
        
        # Validate auth token
        if auth_manager.is_enabled:
            if not auth_manager.validate_key(auth_token):
                error = create_error(ErrorCode.AUTH_FAILED, "Invalid or missing API key")
                await websocket.send_text(error.to_json())
                await websocket.close()
                return
        
        # Create tunnel
        tunnel = await manager.create_tunnel(websocket, local_port, subdomain)
        
        if not tunnel:
            error = create_error(ErrorCode.SUBDOMAIN_TAKEN, f"Subdomain '{subdomain}' is taken")
            await websocket.send_text(error.to_json())
            await websocket.close()
            return
        
        # Send acknowledgment
        ack = create_connect_ack(
            tunnel_id=tunnel.tunnel_id,
            subdomain=tunnel.subdomain,
            public_url=manager.get_public_url(tunnel.subdomain)
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
    
    # Read body
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body_bytes = await request.body()
            if body_bytes:
                body = body_bytes.decode("utf-8", errors="ignore")
        except:
            pass
    
    # Build path with query string
    query = str(request.query_params) if request.query_params else ""
    full_path = f"/{path}"
    if query:
        full_path += f"?{query}"
    
    # Forward request
    start_time = time.time()
    response_data = await manager.forward_request(
        subdomain=subdomain,
        method=method,
        path=full_path,
        headers=headers,
        body=body
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
    
    return Response(
        content=response_data.get("body", ""),
        status_code=status_code,
        headers={"content-type": response_data.get("headers", {}).get("content-type", "text/plain")}
    )
