import asyncio
import json
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class RealtimeHub:
    """In-process WebSocket fan-out. Use Redis pub/sub for multi-worker deploys."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._socket_users: dict[WebSocket, UUID] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)
            self._socket_users[websocket] = user_id

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            user_id = self._socket_users.pop(websocket, None)
            if user_id is None:
                return
            sockets = self._connections.get(user_id)
            if sockets and websocket in sockets:
                sockets.discard(websocket)
                if not sockets:
                    del self._connections[user_id]

    async def send_to_user(self, user_id: UUID, event: str, data: dict) -> None:
        payload = json.dumps({"event": event, "data": data}, default=str)
        async with self._lock:
            sockets = list(self._connections.get(user_id, ()))
        dead: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_text(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            await self.disconnect(websocket)

    async def send_to_users(
        self, user_ids: list[UUID], event: str, data: dict
    ) -> None:
        seen: set[UUID] = set()
        for user_id in user_ids:
            if user_id in seen:
                continue
            seen.add(user_id)
            await self.send_to_user(user_id, event, data)

    @property
    def connection_count(self) -> int:
        return len(self._socket_users)
