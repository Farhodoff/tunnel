"""
Tunnel Client - Connects local server to tunnel server
"""

import asyncio
import json
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import aiohttp
import websockets

from tunnel.core.protocol import (
    Message, MessageType, create_connect_message, create_http_response,
    create_ping, create_pong
)
from tunnel.client.tcp_client import TCPClientHandler


class TunnelClient:
    """Client for creating tunnels"""
    
    def __init__(self, server_url: str, local_port: int,
                 subdomain: Optional[str] = None, auth_token: Optional[str] = None):
        self.server_url = server_url
        self.local_port = local_port
        self.subdomain = subdomain
        self.auth_token = auth_token
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.tunnel_id: Optional[str] = None
        self.public_url: Optional[str] = None
        self.connected = False
        
        self._ping_task: Optional[asyncio.Task] = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0
        self._tcp_handler: Optional[TCPClientHandler] = None
    
    async def connect(self) -> bool:
        """Connect to tunnel server"""
        # Convert HTTP URL to WebSocket URL
        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/tunnel"
        
        print(f"[Client] Connecting to {ws_url}...")
        
        try:
            self.ws = await websockets.connect(ws_url)
            self.session = aiohttp.ClientSession()
            
            # Send connect message
            connect_msg = create_connect_message(
                subdomain=self.subdomain,
                local_port=self.local_port,
                auth_token=self.auth_token
            )
            await self.ws.send(connect_msg.to_json())
            
            # Wait for acknowledgment
            response_data = await self.ws.recv()
            response = Message.from_json(response_data)
            
            if response.msg_type == MessageType.ERROR.value:
                error_msg = response.payload.get("message", "Unknown error")
                print(f"[Client] Connection failed: {error_msg}")
                return False
            
            if response.msg_type == MessageType.CONNECT_ACK.value:
                self.tunnel_id = response.payload.get("tunnel_id")
                self.public_url = response.payload.get("public_url")
                assigned_subdomain = response.payload.get("subdomain")
                self.connected = True
                self._reconnect_delay = 1.0
                
                # Initialize TCP handler
                self._tcp_handler = TCPClientHandler(self.ws.send)
                
                print(f"[Client] ✅ Connected!")
                print(f"[Client] Tunnel ID: {self.tunnel_id}")
                print(f"[Client] Public URL: {self.public_url}")
                print(f"[Client] Local port: {self.local_port}")
                print(f"\n[Client] Your server is accessible at: {self.public_url}\n")
                
                # Start ping task
                self._ping_task = asyncio.create_task(self._ping_loop())
                return True
                
        except Exception as e:
            print(f"[Client] Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        
        if self._tcp_handler:
            await self._tcp_handler.close_all()
        
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
        
        if self.session:
            await self.session.close()
        
        print("[Client] Disconnected")
    
    async def _ping_loop(self):
        """Send periodic ping messages"""
        while self.connected:
            try:
                await asyncio.sleep(30)
                if self.ws and self.connected:
                    ping = create_ping()
                    await self.ws.send(ping.to_json())
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Client] Ping error: {e}")
                break
    
    async def _forward_request(self, request_data: Dict) -> Dict:
        """Forward request to local server (binary-safe via base64)"""
        import base64 as _b64
        method = request_data.get("method", "GET")
        path = request_data.get("path", "/")
        headers = request_data.get("headers", {})
        body = request_data.get("body")
        body_b64 = request_data.get("body_b64")
        request_id = request_data.get("request_id", "")
        
        local_url = f"http://localhost:{self.local_port}{path}"
        
        # Filter hop-by-hop headers; let aiohttp recalc content-length
        _hop = {"host", "content-length", "connection", "transfer-encoding",
                "keep-alive", "proxy-authenticate", "proxy-authorization",
                "te", "trailer", "upgrade"}
        headers = {k: v for k, v in headers.items()
                   if k.lower() not in _hop}
        
        if body_b64:
            try:
                raw_body = _b64.b64decode(body_b64)
            except Exception:
                raw_body = body.encode() if body else None
        elif body:
            raw_body = body.encode() if isinstance(body, str) else body
        else:
            raw_body = None
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with self.session.request(
                method=method,
                url=local_url,
                headers=headers,
                data=raw_body,
                timeout=timeout
            ) as response:
                
                raw_resp = await response.read()
                import base64 as _b64resp
                resp_b64 = _b64resp.b64encode(raw_resp).decode() if raw_resp else None
                try:
                    resp_text = raw_resp.decode("utf-8") if raw_resp else ""
                except UnicodeDecodeError:
                    resp_text = ""
                
                return {
                    "request_id": request_id,
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": resp_text,
                    "body_b64": resp_b64,
                }
                
        except aiohttp.ClientError as e:
            return {
                "request_id": request_id,
                "status_code": 502,
                "headers": {"content-type": "text/plain"},
                "body": f"Cannot connect to local server: {str(e)}"
            }
        except Exception as e:
            return {
                "request_id": request_id,
                "status_code": 500,
                "headers": {"content-type": "text/plain"},
                "body": f"Error: {str(e)}"
            }
    
    async def run(self):
        """Main client loop"""
        while True:
            if not await self.connect():
                # Retry with backoff
                print(f"[Client] Retrying in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay
                )
                continue
            
            try:
                while self.connected:
                    data = await self.ws.recv()
                    message = Message.from_json(data)
                    
                    if message.msg_type == MessageType.HTTP_REQUEST.value:
                        # Forward to local server
                        print(f"[Client] {message.payload.get('method')} {message.payload.get('path')}")
                        response_data = await self._forward_request(message.payload)
                        
                        # Send response back
                        response_msg = create_http_response(
                            request_id=response_data["request_id"],
                            status_code=response_data["status_code"],
                            headers=response_data["headers"],
                            body=response_data.get("body"),
                            body_b64=response_data.get("body_b64"),
                        )
                        await self.ws.send(response_msg.to_json())
                    
                    elif message.msg_type == MessageType.TCP_CONNECT.value:
                        # Handle TCP connect
                        if self._tcp_handler:
                            await self._tcp_handler.handle_tcp_connect(message.payload)
                    
                    elif message.msg_type == MessageType.TCP_DATA.value:
                        # Handle TCP data
                        if self._tcp_handler:
                            await self._tcp_handler.handle_tcp_data(message.payload)
                    
                    elif message.msg_type == MessageType.TCP_CLOSE.value:
                        # Handle TCP close
                        if self._tcp_handler:
                            await self._tcp_handler.handle_tcp_close(message.payload)
                    
                    elif message.msg_type == MessageType.PING.value:
                        # Respond with pong
                        pong = create_pong(message.payload.get("timestamp"))
                        await self.ws.send(pong.to_json())
                    
                    elif message.msg_type == MessageType.ERROR.value:
                        print(f"[Client] Server error: {message.payload.get('message')}")
                        
            except websockets.exceptions.ConnectionClosed:
                print("[Client] Connection closed")
            except Exception as e:
                print(f"[Client] Error: {e}")
            finally:
                await self.disconnect()
                self.connected = False
