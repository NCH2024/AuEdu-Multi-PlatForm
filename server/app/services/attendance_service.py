# server/app/services/attendance_service.py
import json, datetime, asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import SinhVien, DiemDanh, TKBTiet, FaceEmbedding
from app.ai.engine import face_engine


async def _get_embedding_list(image_b64: str, mode: str) -> List[bytes]:
    """
    Gọi AI Engine để trả về list[embedding] (được thực hiện trong thread riêng)
    """
    return await asyncio.to_thread(face_engine.process_attendance_frame, image_b64, mode)


async def _find_best_match(embedding, db: AsyncSession):
    """Trả về FaceEmbedding gần nhất (cosine distance) hoặc None."""
    stmt = (
        select(FaceEmbedding)
        .order_by(FaceEmbedding.embedding.cosine_distance(embedding))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _save_attendance(
    sv_id: int,
    tkb_tiet_id: int,
    attend_date: datetime.date,
    db: AsyncSession,
):
    """
    Kiểm tra trùng lặp, sau đó INSERT vào bảng DiemDanh.
    Nếu có lỗi DB, rollback và trả về False.
    """
    # Kiểm tra đã tồn tại chưa (cùng ngày)
    exists = await db.scalar(
        select(DiemDanh)
        .where(
            DiemDanh.sv_id == sv_id,
            DiemDanh.tkb_tiet_id == tkb_tiet_id,
            DiemDanh.ngay_diem_danh == attend_date,
        )
    )
    if exists:
        return False

    stmt = insert(DiemDanh).values(
        sv_id=sv_id,
        tkb_tiet_id=tkb_tiet_id,
        ngay_diem_danh=attend_date,
        trang_thai="Có mặt",
    )
    try:
        await db.execute(stmt)
        await db.commit()
        return True
    except SQLAlchemyError as err:
        await db.rollback()
        # Log lỗi – ở production bạn nên dùng logger
        print(f"[Attendance Service] DB error: {err}")
        return False


async def handle_attendance_frame(
    websocket,
    tkb_tiet_id: int,
    payload: dict,
    db: AsyncSession,
):
    """
    Hàm chính được gọi từ `attendance/ws.py`.
    - Nhận payload (image, mode, optional date)
    - Chạy AI, so sánh, lưu DB, trả về kết quả qua websocket.
    """
    image_b64 = payload.get("image")
    mode = payload.get("mode", "1")
    date_str = payload.get("date")
    target_date = (
        datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    )
    if not image_b64:
        return  # nothing to do

    # 1️⃣ Lấy danh sách embedding từ AI
    embeddings = await _get_embedding_list(image_b64, mode)

    recognized: list[dict] = []
    already_scanned: set[int] = set()

    for emb in embeddings:
        match = await _find_best_match(emb, db)
        if not match:
            continue
        sv_id = match.sv_id
        if sv_id in already_scanned:
            continue

        # Lấy thông tin sinh viên
        sv = await db.scalar(select(SinhVien).where(SinhVien.id == sv_id))
        if not sv:
            continue

        # Lưu vào DB
        saved = await _save_attendance(sv_id, tkb_tiet_id, target_date, db)
        if not saved:
            # Đã tồn tại hoặc lỗi DB → bỏ qua
            continue

        already_scanned.add(sv_id)
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
