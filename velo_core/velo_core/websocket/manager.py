import asyncio
import json
import logging
from typing import Set
from fastapi import WebSocket
from velo_core.models.schemas import WSMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: WSMessage, websocket: WebSocket):
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def broadcast(self, message: WSMessage):
        if not self.active_connections:
            return
        message_json = message.model_dump_json()
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)
        for conn in disconnected:
            await self.disconnect(conn)

    async def broadcast_json(self, data: dict):
        await self.broadcast(WSMessage.model_validate(data))

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()