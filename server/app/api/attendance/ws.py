# server/app/api/attendance/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.attendance_service import handle_attendance_frame
import json

router = APIRouter()

@router.websocket("/ws/attendance/{tkb_tiet_id}")
async def attendance_websocket(
    websocket: WebSocket,
    tkb_tiet_id: int,
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            await handle_attendance_frame(websocket, tkb_tiet_id, payload, db)
    except WebSocketDisconnect:
        print(f"[Server] WebSocket ngắt kết nối: {tkb_tiet_id}")
    except Exception as exc:
        print(f"[Server] WebSocket error: {exc}")
