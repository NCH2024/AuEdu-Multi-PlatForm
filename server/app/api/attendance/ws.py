"""
server/app/api/attendance/ws.py
================================
WebSocket Endpoint – Điểm Danh Thời Gian Thực

Kiến trúc: Producer – Consumer (Async Queue)
─────────────────────────────────────────────
                   ┌──────────────┐
   Client ──WS──►  │   Producer   │  ──► asyncio.Queue(maxsize=3)
                   └──────────────┘               │
                                                  ▼
                                         ┌──────────────┐
                                         │   Consumer   │ (asyncio.Task)
                                         │  (AI Worker) │
                                         └──────────────┘
                                                  │
                                                  ▼
                                         handle_attendance_frame()
                                                  │
                                                  ▼
                                         WebSocket ◄─── JSON Response

Vấn đề giải quyết:
    - Nếu AI xử lý chậm hơn tốc độ Client gửi frame (thường xảy ra trên CPU),
      Producer không bị block – frame cũ nhất sẽ bị "drop" (Drop-Oldest Policy)
      để nhường chỗ cho frame mới nhất (real-time priority).
    - Consumer chạy ngầm dưới dạng asyncio.Task, tách biệt hoàn toàn với
      vòng lặp nhận tin nhắn của Producer → không có điểm blocking.

Tác giả: AuEdu Senior AI Team
"""

import json
import asyncio
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import GiangVien
from app.services.attendance_service import handle_attendance_frame
from app.core.security import verify_token
from app.core.config import MAX_QUEUE_SIZE, DROP_OLDEST


router = APIRouter()


@router.websocket("/{tkb_tiet_id}")
async def attendance_websocket(
    websocket: WebSocket,
    tkb_tiet_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint WebSocket Điểm Danh Bất Đồng Bộ.

    URL: ws://<host>/api/attendance/ws/{tkb_tiet_id}?token=<JWT>

    Lifecycle:
        1. Xác thực JWT token → Lấy thông tin Giảng Viên.
        2. Khởi tạo asyncio.Queue(maxsize=3) – Hàng đợi frame.
        3. Tạo Consumer Task chạy ngầm (asyncio.create_task).
        4. Vòng lặp Producer: Nhận frame → Drop-Oldest nếu đầy → Đẩy vào Queue.
        5. Khi WebSocket ngắt → Cancel Consumer Task an toàn → Đóng kết nối.

    Payload Client gửi lên (JSON string):
        {
            "image": "<base64_string>",   // Ảnh frame camera (JPEG/PNG base64)
            "mode": "1" | "all",          // Chế độ nhận diện
            "date": "YYYY-MM-DD",         // Ngày điểm danh (tuỳ chọn)
            "vitri": "Phòng 101",         // Vị trí (tuỳ chọn)
            "device_id": "...",           // ID thiết bị (tuỳ chọn)
            "client_version": "1.0.0"    // Phiên bản Client (tuỳ chọn)
        }

    Response Server gửi về (JSON string):
        {
            "status": "success",
            "students": [
                {
                    "id": 123,
                    "name": "Nguyễn Văn A",
                    "time": "09:30:15",
                    "status": "Có mặt",
                    "score": 0.3142,
                    "vitri": "Tại lớp",
                    "is_new": true
                }
            ]
        }
    """
    # ==========================================================================
    # BƯỚC 1: XÁC THỰC TOKEN JWT
    # ==========================================================================
    try:
        user_payload = await verify_token(token)
    except Exception as e:
        print(f"[WS Attendance] Lỗi xác thực token: {e}")
        # Cần accept() trước mới có thể close() với mã lỗi
        await websocket.accept()
        await websocket.close(code=1008, reason="Token không hợp lệ hoặc đã hết hạn")
        return

    if not user_payload:
        await websocket.accept()
        await websocket.close(code=1008, reason="Token không hợp lệ")
        return

    # Lấy UUID của Supabase auth và tìm ID Integer trong bảng GiangVien
    auth_uuid: str = user_payload.get("id")
    gv_id: int | None = await db.scalar(
        select(GiangVien.id).where(GiangVien.auth_id == auth_uuid)
    )

    # Chấp nhận kết nối WebSocket
    await websocket.accept()
    print(
        f"[WS Attendance] ✓ Kết nối mới | "
        f"TKB_Tiet_ID={tkb_tiet_id} | GV_ID={gv_id}"
    )

    # ==========================================================================
    # BƯỚC 2: KHỞI TẠO HÀNG ĐỢI FRAME (ASYNC QUEUE)
    # ==========================================================================
    # maxsize=3: Giới hạn tối đa 3 frame chờ xử lý trong queue.
    # Con số nhỏ để tránh tích trữ frame cũ khi AI xử lý chậm.
    frame_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

    # ==========================================================================
    # BƯỚC 3: ĐỊNH NGHĨA CONSUMER (AI Worker)
    # ==========================================================================
    async def consumer_task() -> None:
        """
        Consumer Task: Chạy ngầm liên tục, lấy frame ra khỏi Queue và
        đưa qua pipeline AI → ghi DB → phản hồi WebSocket.

        Vòng đời:
            - Chạy liên tục cho đến khi bị cancel() từ Producer khi WS ngắt.
            - asyncio.CancelledError: Thoát vòng lặp một cách an toàn.
            - Các Exception khác: Log và tiếp tục (không làm crash toàn bộ worker).
        """
        print(f"[WS Consumer] ▶ Consumer AI Worker khởi động cho TKB_Tiet_ID={tkb_tiet_id}")

        while True:
            try:
                # Chờ cho đến khi có frame mới trong queue (blocking async wait)
                payload: dict = await frame_queue.get()

                # Gọi dịch vụ điểm danh: AI Engine + DB + WebSocket response
                # Đây là hàm async nên không block event loop chính
                await handle_attendance_frame(
                    websocket=websocket,
                    tkb_tiet_id=tkb_tiet_id,
                    payload=payload,
                    db=db,
                    giangvien_id=gv_id,
                )

                # Báo hiệu Queue rằng phần tử này đã được xử lý xong
                frame_queue.task_done()

            except asyncio.CancelledError:
                # Được cancel() gọi từ khối finally của Producer khi WS đóng
                # Thoát vòng lặp an toàn, không re-raise
                print(f"[WS Consumer] ■ Consumer Task bị huỷ an toàn cho TKB_Tiet_ID={tkb_tiet_id}")
                break

            except Exception as exc:
                # Lỗi trong quá trình xử lý AI hoặc ghi DB – Log và tiếp tục
                # Không để 1 frame lỗi làm sập toàn bộ Consumer Worker
                print(f"[WS Consumer][ERROR] Lỗi khi xử lý frame: {exc}")
                traceback.print_exc()
                # Đảm bảo task_done() được gọi ngay cả khi có lỗi
                # để tránh Queue bị "kẹt" trong trạng thái unfinished
                try:
                    frame_queue.task_done()
                except ValueError:
                    pass  # task_done() gọi nhiều hơn số lần get() – bỏ qua

    # Tạo Consumer Task và cho nó chạy ngầm song song với Producer
    worker: asyncio.Task = asyncio.create_task(consumer_task())

    # ==========================================================================
    # BƯỚC 4: VÒNG LẶP PRODUCER – Nhận Frame từ Client
    # ==========================================================================
    try:
        while True:
            # Đợi tin nhắn từ Client (blocking async – không chiếm CPU)
            raw_data: str = await websocket.receive_text()

            # Giải mã JSON payload từ Client
            try:
                payload: dict = json.loads(raw_data)
            except json.JSONDecodeError:
                print(f"[WS Producer][WARN] Nhận được dữ liệu không hợp lệ (JSON parse error), bỏ qua.")
                continue

            # ------------------------------------------------------------------
            # DROP-OLDEST POLICY – Chính sách Loại Frame Cũ Khi Queue Đầy
            # ------------------------------------------------------------------
            # Nếu Consumer đang chậm (AI nặng) và Queue đã có đủ 3 frame chờ,
            # ta loại bỏ frame cũ nhất (đầu queue) để nhường chỗ cho frame mới nhất.
            # Điều này đảm bảo hệ thống luôn xử lý ảnh "thời gian thực" nhất có thể.
            if frame_queue.full():
                if DROP_OLDEST:
                    try:
                        dropped_payload = frame_queue.get_nowait()
                        frame_queue.task_done()
                        print(
                            f"[WS Producer] ⚡ Queue đầy ({frame_queue.maxsize} slots) – "
                            f"Đã loại frame cũ, ưu tiên frame thời gian thực mới nhất."
                        )
                    except asyncio.QueueEmpty:
                        pass
                else:
                    # back-pressure: wait until consumer frees a slot
                    await frame_queue.put(payload)
                    continue

            # Đẩy frame mới nhất vào cuối Queue cho Consumer xử lý
            await frame_queue.put(payload)
            print(f"[WS Queue] size={frame_queue.qsize()}")

    except WebSocketDisconnect:
        # Client chủ động ngắt kết nối (đóng tab, mất mạng, v.v.)
        print(f"[WS Producer] ✗ WebSocket ngắt kết nối bình thường | TKB_Tiet_ID={tkb_tiet_id}")

    except Exception as exc:
        # Lỗi bất ngờ trong vòng lặp nhận tin nhắn
        print(f"[WS Producer][ERROR] Lỗi vòng lặp Producer: {exc}")
        traceback.print_exc()

    finally:
        # =======================================================================
        # BƯỚC 5: DỌN DẸP – Huỷ Consumer Task và đóng kết nối an toàn
        # =======================================================================
        print(f"[WS Attendance] 🔒 Đang dọn dẹp kết nối TKB_Tiet_ID={tkb_tiet_id}...")

        # Yêu cầu hủy Consumer Task (sẽ ném CancelledError vào vòng lặp while True)
        worker.cancel()

        # Đợi Consumer Task kết thúc sạch sẽ trước khi thoát
        # (await ensure cleanup code trong consumer_task có thể hoàn thành)
        try:
            await asyncio.wait_for(worker, timeout=3.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            # CancelledError: Bình thường sau cancel()
            # TimeoutError: Consumer quá chậm → buộc thoát sau 3 giây
            pass

        # Đóng WebSocket (bỏ qua nếu đã đóng)
        try:
            await websocket.close(code=1000, reason="Phiên điểm danh kết thúc")
        except Exception:
            pass  # Kết nối đã đóng hoặc không còn valid

        print(f"[WS Attendance] ✓ Đã dọn dẹp hoàn tất | TKB_Tiet_ID={tkb_tiet_id}")