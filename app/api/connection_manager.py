import contextlib
import logging
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Map client_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # Map client_id -> Orchestrator Instance (For API Control)
        self.orchestrators: dict[str, Any] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        # Enforce "Tunnel": If this client already has a connection, close it.
        if client_id in self.active_connections:
            logging.warning(f"Closing zombie connection for client {client_id}")
            # We expect the old loop to crash/exit, triggering its finally block.
            # But we handle the cleanup logic carefully in disconnect()
            with contextlib.suppress(Exception):
                await self.active_connections[client_id].close()

        await websocket.accept()
        self.active_connections[client_id] = websocket

    def register_orchestrator(self, client_id: str, orchestrator: Any):
        """Register orchestrator instance for API access."""
        self.orchestrators[client_id] = orchestrator

    def get_orchestrator(self, client_id: str) -> Any:
        """Get orchestrator instance by ID."""
        return self.orchestrators.get(client_id)

    def disconnect(self, client_id: str, websocket: WebSocket):
        # Only remove if it's the SAME connection (avoid race where old socket kills new socket's entry)
        if client_id in self.active_connections and self.active_connections[client_id] == websocket:
            del self.active_connections[client_id]

        # Cleanup orchestrator ref if matches (simple cleanup)
        if client_id in self.orchestrators:
            del self.orchestrators[client_id]

manager = ConnectionManager()
