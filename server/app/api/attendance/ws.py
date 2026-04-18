# server/app/api/attendance/ws.py
import json, datetime, asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from app.db.session import get_db
from app.db.models import SinhVien, DiemDanh, TKBTiet, FaceEmbedding
from app.ai.engine import face_engine   

router = APIRouter()


@router.websocket("/ws/attendance/{tkb_tiet_id}")
async def attendance_websocket(
    websocket: WebSocket,
    tkb_tiet_id: int,
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()
    print(f"[Server] WebSocket kết nối cho Tiết: {tkb_tiet_id}")

    session_scanned_ids: set[int] = set()

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            img_b64 = payload.get("image")
            mode = payload.get("mode", "1")
            target_date_str = payload.get("date")
            target_date = (
                datetime.date.fromisoformat(target_date_str)
                if target_date_str
                else datetime.date.today()
            )
            if not img_b64:
                continue

            # Nhận embedding từ AI (được chạy trong thread riêng để không block)
            embeddings = await asyncio.to_thread(
                face_engine.process_attendance_frame, img_b64, mode
            )
            recognized: list[dict] = []

            for emb in embeddings:
                # Tìm sinh viên gần nhất (cosine distance)
                stmt = (
                    select(FaceEmbedding)
                    .order_by(FaceEmbedding.embedding.cosine_distance(emb))
                    .limit(1)
                )
                result = await db.execute(stmt)
                match = result.scalar_one_or_none()
                if not match:
                    continue

                sv_id = match.sv_id
                if sv_id in session_scanned_ids:
                    continue

                # Kiểm tra sinh viên đã tồn tại
                sv = await db.scalar(select(SinhVien).where(SinhVien.id == sv_id))
                if not sv:
                    continue

                # Kiểm tra trùng lặp (cùng ngày)
                exists = await db.scalar(
                    select(DiemDanh)
                    .where(
                        DiemDanh.sv_id == sv_id,
                        DiemDanh.tkb_tiet_id == tkb_tiet_id,
                        DiemDanh.ngay_diem_danh == target_date,
                    )
                )
                if exists:
                    continue

                # Lưu vào DB
                stmt_ins = insert(DiemDanh).values(
                    sv_id=sv.id,
                    tkb_tiet_id=tkb_tiet_id,
                    ngay_diem_danh=target_date,
                    trang_thai="Có mặt",
                )
                await db.execute(stmt_ins)
                await db.commit()

                session_scanned_ids.add(sv_id)
                recognized.append(
                    {
                        "id": str(sv.id),
                        "name": f"{sv.hodem} {sv.ten}".strip(),
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    }
                )

            if recognized:
                await websocket.send_text(
                    json.dumps({"status": "success", "students": recognized})
                )
    except WebSocketDisconnect:
        print(f"[Server] WebSocket ngắt kết nối: {tkb_tiet_id}")
    except Exception as exc:
        print(f"[Server] WebSocket error: {exc}")
