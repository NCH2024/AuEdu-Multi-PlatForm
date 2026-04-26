from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import GiangVien
from app.services.attendance_service import handle_attendance_frame
from app.core.security import verify_token 
import json
import asyncio
import traceback

router = APIRouter()

@router.websocket("/{tkb_tiet_id}")
async def attendance_websocket(
    websocket: WebSocket,
    tkb_tiet_id: int,
    token: str = Query(...), 
    db: AsyncSession = Depends(get_db),
):
    """
    Luồng WebSockets Bất Đồng Bộ Điểm Danh:
    Sử dụng kiến trúc Producer-Consumer (Hàng đợi) để chống tình trạng Blocking/Timeout
    khi thuật toán AI trên Server xử lý chậm hơn tốc độ Client gửi Frame lên.
    """
    try:
        user_payload = await verify_token(token)
    except Exception as e:
        print(f"[WS] Lỗi xác thực Token: {e}")
        await websocket.accept() 
        await websocket.close(code=1008, reason="Token không hợp lệ hoặc đã hết hạn")
        return
        
    if not user_payload:
        await websocket.accept()
        await websocket.close(code=1008, reason="Token không hợp lệ")
        return
        
    # Lấy UUID của Supabase và đối chiếu tìm ID Integer của Giảng Viên
    auth_uuid = user_payload.get("id")
    gv_id = await db.scalar(select(GiangVien.id).where(GiangVien.auth_id == auth_uuid))
    
    # Chấp nhận kết nối
    await websocket.accept()
    print(f"[WebSocket] Đã chấp nhận kết nối cho tiết: {tkb_tiet_id} (Giảng viên ID: {gv_id})")
    
    # -------------------------------------------------------------------------
    # KIẾN TRÚC PRODUCER - CONSUMER (CHỐNG NGHẼN BẰNG QUEUE)
    # -------------------------------------------------------------------------
    # maxsize=5: Chỉ giữ tối đa 5 khung hình trong hàng đợi để tránh tràn RAM
    frame_queue = asyncio.Queue(maxsize=5)

    # 1. CONSUMER: Luồng chạy ngầm liên tục lấy ảnh ra khỏi Queue để xử lý AI
    async def consumer_task():
        while True:
            try:
                # Đợi cho đến khi có khung hình mới
                payload = await frame_queue.get()
                
                # Gọi hàm xử lý AI lõi (sẽ chạy thuật toán InsightFace khá nặng)
                await handle_attendance_frame(websocket, tkb_tiet_id, payload, db, gv_id)
                
                # Đánh dấu đã xử lý xong phần tử
                frame_queue.task_done()
                
            except asyncio.CancelledError:
                break # Luồng bị hủy an toàn từ bên ngoài
            except Exception as exc:
                print(f"[Consumer Worker] Lỗi xử lý frame: {exc}")
                traceback.print_exc()

    # Khởi tạo Task chạy ngầm cho Consumer
    worker = asyncio.create_task(consumer_task())
    
    # 2. PRODUCER: Luồng chính nhận Frame liên tục từ Client và đẩy vào Queue
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # KỸ THUẬT "DROP OLDEST" (Loại bỏ khung hình cũ nhất khi nghẽn)
            # Nếu Server xử lý chậm, Queue đầy -> Drop frame cũ nhất để lấy chỗ cho frame thời gian thực mới nhất
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                    frame_queue.task_done()
                    print("[WS Queue] Hàng đợi đầy, ném bỏ frame cũ để nhận frame thời gian thực mới nhất.")
                except asyncio.QueueEmpty:
                    pass
            
            # Đẩy frame mới nhất vào hàng đợi cho Consumer xử lý
            await frame_queue.put(payload)
            
    except WebSocketDisconnect:
        print(f"[Server] WebSocket ngắt kết nối: {tkb_tiet_id}")
    except Exception as exc:
        print(f"[Server] Lỗi vòng lặp WebSocket: {exc}")
        traceback.print_exc()
    finally:
        # 3. CLEANUP: Hủy an toàn tiến trình xử lý ngầm khi ngắt kết nối
        worker.cancel()
        try:
            await websocket.close(code=1011, reason="Lỗi máy chủ nội bộ hoặc đóng kết nối")
        except:
            pass