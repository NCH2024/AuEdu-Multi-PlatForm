from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import GiangVien
from app.services.attendance_service import handle_attendance_frame
from app.core.security import verify_token 
import json

router = APIRouter()

@router.websocket("/{tkb_tiet_id}")
async def attendance_websocket(
    websocket: WebSocket,
    tkb_tiet_id: int,
    token: str = Query(...), 
    db: AsyncSession = Depends(get_db),
):
    try:
        # 1. Giải mã token an toàn
        user_payload = await verify_token(token)
    except HTTPException:
        await websocket.close(code=1008, reason="Token không hợp lệ")
        return
    except Exception as e:
        print(f"[WS] Lỗi xác thực: {e}")
        await websocket.close(code=1011, reason="Lỗi máy chủ nội bộ")
        return
            
    if not user_payload:
        await websocket.close(code=1008, reason="Token không hợp lệ")
        return
        
    # 2. Lấy UUID của Supabase và đối chiếu tìm ID Integer của Giảng Viên
    auth_uuid = user_payload.get("id")
    gv_id = await db.scalar(select(GiangVien.id).where(GiangVien.auth_id == auth_uuid))
    
    # 3. Chấp nhận kết nối
    await websocket.accept()
    print(f"[WebSocket] Đã chấp nhận kết nối cho tiết: {tkb_tiet_id} (Giảng viên ID: {gv_id})")
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            # Truyền gv_id chuẩn vào CSDL
            await handle_attendance_frame(websocket, tkb_tiet_id, payload, db, gv_id)
            
    except WebSocketDisconnect:
        print(f"[Server] WebSocket ngắt kết nối: {tkb_tiet_id}")
    except Exception as exc:
        print(f"[Server] Lỗi xử lý Frame WebSocket: {exc}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close(code=1011, reason="Lỗi máy chủ nội bộ")
        except:
            pass