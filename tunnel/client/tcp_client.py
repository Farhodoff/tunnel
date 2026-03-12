"""
TCP Client - Handle TCP connections for client
"""

import asyncio
import base64
from typing import Dict, Optional
from dataclasses import dataclass

from tunnel.core.protocol import (
    Message, MessageType, create_tcp_data, create_tcp_close
)


@dataclass
class ClientTCPConnection:
    """Client-side TCP connection"""
    connection_id: str
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    is_active: bool = True


class TCPClientHandler:
    """Handle TCP connections on client side"""
    
    def __init__(self, websocket_send):
        self.websocket_send = websocket_send
        self._connections: Dict[str, ClientTCPConnection] = {}
    
    async def handle_tcp_connect(self, payload: Dict):
        """Handle TCP connect request from server"""
        connection_id = payload.get("connection_id")
        remote_host = payload.get("remote_host")
        remote_port = payload.get("remote_port")
        
        try:
            # Connect to local service
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(remote_host, remote_port),
                timeout=10
            )
            
            conn = ClientTCPConnection(
                connection_id=connection_id,
                reader=reader,
                writer=writer
            )
            self._connections[connection_id] = conn
            
            # Start relaying data
            asyncio.create_task(self._relay_from_local(conn))
            
            print(f"[TCP Client] Connected to {remote_host}:{remote_port}")
            
        except Exception as e:
            print(f"[TCP Client] Connection failed: {e}")
            # Send close message
            close_msg = create_tcp_close(connection_id, str(e))
            await self.websocket_send(close_msg.to_json())
    
    async def _relay_from_local(self, conn: ClientTCPConnection):
        """Relay data from local service to server"""
        try:
            while conn.is_active:
                data = await conn.reader.read(4096)
                if not data:
                    break
                
                # Encode and send
                encoded = base64.b64encode(data).decode()
                data_msg = create_tcp_data(conn.connection_id, encoded, "in")
                await self.websocket_send(data_msg.to_json())
                
        except Exception as e:
            print(f"[TCP Client] Relay error: {e}")
        finally:
            await self.close_connection(conn.connection_id, "Local service closed")
    
    async def handle_tcp_data(self, payload: Dict):
        """Handle TCP data from server"""
        connection_id = payload.get("connection_id")
        data = payload.get("data")
        direction = payload.get("direction", "out")
        
        conn = self._connections.get(connection_id)
        if not conn or not conn.is_active:
            return
        
        if direction == "out":
            # Data from remote client to local service
            try:
                decoded = base64.b64decode(data)
                conn.writer.write(decoded)
                await conn.writer.drain()
            except Exception as e:
                print(f"[TCP Client] Write error: {e}")
                await self.close_connection(connection_id, str(e))
    
    async def handle_tcp_close(self, payload: Dict):
        """Handle TCP close from server"""
        connection_id = payload.get("connection_id")
        await self.close_connection(connection_id, payload.get("reason"))
    
    async def close_connection(self, connection_id: str, reason: Optional[str] = None):
        """Close TCP connection"""
        conn = self._connections.pop(connection_id, None)
        if conn:
            conn.is_active = False
            try:
                conn.writer.close()
                await conn.writer.wait_closed()
            except:
                pass
            
            # Notify server
            close_msg = create_tcp_close(connection_id, reason)
            await self.websocket_send(close_msg.to_json())
            
            print(f"[TCP Client] Closed connection {connection_id}: {reason or 'Unknown'}")
    
    async def close_all(self):
        """Close all connections"""
        for connection_id in list(self._connections.keys()):
            await self.close_connection(connection_id, "Client shutting down")
