# server/app/core/broadcaster.py
import asyncio
import json
from typing import Set
from fastapi import WebSocket

class Broadcaster:
    """
    Quản lý các kết nối WebSocket và phát tin nhắn (broadcast) tới nhiều client.
    Dành cho việc giám sát Admin thời gian thực.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Broadcaster, cls).__new__(cls)
            cls._instance.active_connections: Set[WebSocket] = set()
        return cls._instance

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"[Broadcaster] Admin connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[Broadcaster] Admin disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Gửi tin nhắn tới tất cả Admin đang kết nối."""
        if not self.active_connections:
            return

        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        # Tạo bản sao của tập hợp để tránh lỗi khi remove trong lúc lặp
        tasks = []
        for connection in list(self.active_connections):
            tasks.append(self._send_message(connection, message_str, disconnected))
        
        if tasks:
            await asyncio.gather(*tasks)

        # Dọn dẹp các kết nối lỗi
        for ws in disconnected:
            self.disconnect(ws)

    async def _send_message(self, websocket: WebSocket, message: str, disconnected: Set[WebSocket]):
        try:
            await websocket.send_text(message)
        except Exception:
            disconnected.add(websocket)

# Singleton instance
broadcaster = Broadcaster()
