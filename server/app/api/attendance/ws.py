from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.attendance_service import handle_attendance_frame
from app.core.security import verify_token # Import hàm verify token của dự án
import json

router = APIRouter()

@router.websocket("/ws/attendance/{tkb_tiet_id}")
async def attendance_websocket(
    websocket: WebSocket,
    tkb_tiet_id: int,
    token: str = Query(...), # Bắt buộc phải có token truyền qua query param: ?token=...
    db: AsyncSession = Depends(get_db),
):
    # 1. Xác thực Giảng viên
    user_payload = await verify_token(token) # Hàm này anh đã có bên security.py
    if not user_payload:
        await websocket.close(code=1008, reason="Invalid authentication credentials")
        return
        
    giangvien_id = user_payload.get("user_id") # Cấu trúc tùy thuộc JWT của anh

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            # Truyền giangvien_id xuống service
            await handle_attendance_frame(websocket, tkb_tiet_id, payload, db, giangvien_id)
    except WebSocketDisconnect:
        print(f"[Server] WebSocket ngắt kết nối: {tkb_tiet_id}")
    except Exception as exc:
        print(f"[Server] WebSocket error: {exc}")