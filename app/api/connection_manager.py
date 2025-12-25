from fastapi import WebSocket
from typing import Dict
import logging

class ConnectionManager:
    def __init__(self):
        # Map client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        # Enforce "Tunnel": If this client already has a connection, close it.
        if client_id in self.active_connections:
            logging.warning(f"Closing zombie connection for client {client_id}")
            try:
                await self.active_connections[client_id].close()
            except Exception:
                pass
            
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

manager = ConnectionManager()
