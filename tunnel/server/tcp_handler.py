"""
TCP Handler - Raw TCP tunneling support
"""

import asyncio
import base64
import uuid
from typing import Dict, Optional
from dataclasses import dataclass, field

from tunnel.utils.logging import setup_logger

logger = setup_logger("tunnel.tcp")

from tunnel.core.protocol import (
    Message, MessageType, create_tcp_connect, create_tcp_data, create_tcp_close
)


@dataclass
class TCPConnection:
    """TCP connection through tunnel"""
    connection_id: str
    tunnel_id: str
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    remote_host: str
    remote_port: int
    is_active: bool = True


class TCPHandler:
    """Handle TCP tunneling"""
    
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self._connections: Dict[str, TCPConnection] = {}
        self._servers: Dict[str, asyncio.Server] = {}  # port -> server
    
    def get_listener_port(self, tunnel_id: str) -> Optional[int]:
        """Get actual public port for tunnel (supports port 0 auto-assign)"""
        server = self._servers.get(tunnel_id)
        if not server or not server.sockets:
            return None
        return server.sockets[0].getsockname()[1]

    def is_port_in_use(self, port: int) -> bool:
        """Check if public TCP port already taken by another tunnel"""
        if not port:
            return False
        for server in self._servers.values():
            for sock in (server.sockets or []):
                try:
                    if sock.getsockname()[1] == port:
                        return True
                except Exception:
                    continue
        return False

    async def start_tcp_listener(self, port: int, tunnel_id: str, remote_host: str, remote_port: int):
        """Start TCP listener for tunnel"""
        
        async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            """Handle incoming TCP connection"""
            connection_id = str(uuid.uuid4())[:8]
            
            conn = TCPConnection(
                connection_id=connection_id,
                tunnel_id=tunnel_id,
                reader=reader,
                writer=writer,
                remote_host=remote_host,
                remote_port=remote_port
            )
            self._connections[connection_id] = conn
            
            # Get tunnel websocket
            tunnel = await self.connection_manager.get_by_id(tunnel_id)
            if not tunnel:
                writer.close()
                return
            
            # Send TCP_CONNECT message
            connect_msg = create_tcp_connect(connection_id, remote_host, remote_port)
            await tunnel.websocket.send_text(connect_msg.to_json())
            
            # Start relaying data
            try:
                while conn.is_active:
                    data = await reader.read(4096)
                    if not data:
                        break
                    
                    # Encode and send through tunnel
                    encoded = base64.b64encode(data).decode()
                    data_msg = create_tcp_data(connection_id, encoded, "out")
                    await tunnel.websocket.send_text(data_msg.to_json())
                    
            except Exception as e:
                logger.error(f"Connection error: {e}")
            finally:
                await self.close_connection(connection_id, "Client disconnected")
        
        if port and self.is_port_in_use(port):
            raise OSError(f"TCP port {port} already in use")

        # Start server (port=0 lets OS auto-assign)
        server = await asyncio.start_server(handle_client, '0.0.0.0', port or 0)
        self._servers[tunnel_id] = server
        
        actual = self.get_listener_port(tunnel_id)
        logger.info(f"Started listener on port {actual} for tunnel {tunnel_id}")
        return server
    
    async def handle_tcp_data(self, tunnel_id: str, payload: Dict):
        """Handle TCP data from client"""
        connection_id = payload.get("connection_id")
        data = payload.get("data")
        direction = payload.get("direction", "in")
        
        conn = self._connections.get(connection_id)
        if not conn or not conn.is_active:
            return
        
        if direction == "in":
            # Data from local service to remote client
            try:
                decoded = base64.b64decode(data)
                conn.writer.write(decoded)
                await conn.writer.drain()
            except Exception as e:
                logger.error(f"Write error: {e}")
                await self.close_connection(connection_id, str(e))
    
    async def handle_tcp_close(self, tunnel_id: str, payload: Dict):
        """Handle TCP close from client"""
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
            logger.info(f"Closed connection {connection_id}: {reason or 'Unknown'}")
    
    async def stop_tcp_listener(self, tunnel_id: str):
        """Stop TCP listener for tunnel"""
        server = self._servers.pop(tunnel_id, None)
        if server:
            server.close()
            await server.wait_closed()
            logger.info(f"Stopped listener for tunnel {tunnel_id}")
        
        # Close all connections for this tunnel
        connections_to_close = [
            cid for cid, conn in self._connections.items()
            if conn.tunnel_id == tunnel_id
        ]
        for cid in connections_to_close:
            await self.close_connection(cid, "Tunnel closed")
