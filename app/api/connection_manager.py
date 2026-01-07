import logging

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Map client_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        # Enforce "Tunnel": If this client already has a connection, close it.
        if client_id in self.active_connections:
            logging.warning(f"Closing zombie connection for client {client_id}")
            try:
                # We expect the old loop to crash/exit, triggering its finally block.
                # But we handle the cleanup logic carefully in disconnect()
                await self.active_connections[client_id].close()
            except Exception:
                pass

        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str, websocket: WebSocket):
        # Only remove if it's the SAME connection (avoid race where old socket kills new socket's entry)
        if client_id in self.active_connections and self.active_connections[client_id] == websocket:
            del self.active_connections[client_id]

manager = ConnectionManager()
