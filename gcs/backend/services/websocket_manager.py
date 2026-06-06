"""
Eqaab GCS — WebSocket Connection Manager

Manages WebSocket connections from GCS frontend clients.
Broadcasts telemetry, detections, and alerts to all connected clients.
"""

import json
import asyncio
import logging
from fastapi import WebSocket
from typing import Any

logger = logging.getLogger("eqaab.ws")


class ConnectionManager:
    """Manages multiple WebSocket connections from GCS clients."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        client_count = len(self.active_connections)
        logger.info(f"GCS client connected. Total clients: {client_count}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        client_count = len(self.active_connections)
        logger.info(f"GCS client disconnected. Total clients: {client_count}")

    async def broadcast(self, data: dict | Any):
        """Send data to all connected GCS clients."""
        if not self.active_connections:
            return

        # Convert Pydantic model to dict if needed
        if hasattr(data, "model_dump"):
            message = data.model_dump()
        elif isinstance(data, dict):
            message = data
        else:
            message = data

        payload = json.dumps(message)

        # Send to all, collect dead connections
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead.append(connection)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)
            logger.info(f"Cleaned {len(dead)} dead connection(s)")

    async def send_to(self, websocket: WebSocket, data: dict | Any):
        """Send data to a specific client."""
        if hasattr(data, "model_dump"):
            message = data.model_dump()
        else:
            message = data
        await websocket.send_text(json.dumps(message))

    @property
    def client_count(self) -> int:
        return len(self.active_connections)
