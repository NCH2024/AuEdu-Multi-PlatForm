# server/app/api/admin/ws_monitor.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import verify_token
from app.core.broadcaster import broadcaster

router = APIRouter()

@router.websocket("/monitor")
async def admin_monitoring_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint dành cho Admin để giám sát điểm danh toàn hệ thống.
    URL: ws://<host>/api/admin/attendance/ws/monitor?token=<JWT>
    """
    try:
        # Xác thực quyền Admin
        payload = await verify_token(token)
        if not payload or payload.get("role") not in ["admin", "super_admin"]:
            await websocket.accept()
            await websocket.close(code=1008, reason="Unauthorized: Admin access required")
            return
            
        # Chấp nhận kết nối qua Broadcaster
        await broadcaster.connect(websocket)
        
        # Giữ kết nối mở
        try:
            while True:
                # Chờ nhận tin nhắn (admin có thể gửi ping hoặc yêu cầu gì đó, hiện tại chỉ để giữ connection)
                data = await websocket.receive_text()
                # Có thể xử lý lệnh từ admin ở đây nếu cần
        except WebSocketDisconnect:
            broadcaster.disconnect(websocket)
        except Exception as e:
            print(f"[WS Monitor] Error: {e}")
            broadcaster.disconnect(websocket)
            
    except Exception as e:
        print(f"[WS Monitor] Auth Error: {e}")
        # Nếu chưa accept thì không cần close
        try:
            await websocket.close(code=1008, reason="Auth failed")
        except: pass
