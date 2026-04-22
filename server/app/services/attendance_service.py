# server/app/services/attendance_service.py
import json, datetime, asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import SinhVien, DiemDanh, TKBTiet, FaceEmbedding
from app.ai.engine import face_engine


async def _get_embedding_list(image_b64: str, mode: str) -> List[bytes]:
    """
    Gọi AI Engine để trả về list[embedding] (được thực hiện trong thread riêng)
    """
    return await asyncio.to_thread(face_engine.process_attendance_frame, image_b64, mode)


async def _find_best_match(embedding, db: AsyncSession):
    """Trả về (FaceEmbedding, khoảng_cách_cosine) gần nhất hoặc (None, None)."""
    distance = FaceEmbedding.embedding.cosine_distance(embedding)
    stmt = (
        select(FaceEmbedding, distance.label('score'))
        .order_by(distance)
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    if row:
        return row[0], row[1] # Trả về tuple (match, score)
    return None, None


async def _save_attendance(
    sv_id: int, tkb_tiet_id: int, attend_date: datetime.date, db: AsyncSession,
    vitri: str = None, device_id: str = None, client_version: str = None,
    confidence_score: float = None, created_by: int = None
):
    try:
        # 1. Kiểm tra xem đã có bản ghi nào chưa
        stmt = select(DiemDanh).where(
            DiemDanh.sv_id == sv_id,
            DiemDanh.tkb_tiet_id == tkb_tiet_id,
            DiemDanh.ngay_diem_danh == attend_date
        )
        result = await db.execute(stmt)
        existing_record = result.scalar_one_or_none()

        if existing_record:
            if existing_record.trang_thai == "Có mặt":
                return "ALREADY_PRESENT" # Đã điểm danh rồi
            else:
                # Đang Vắng -> Cập nhật thành Có mặt (Cho phép quét lại)
                existing_record.trang_thai = "Có mặt"
                existing_record.vitri = vitri
                existing_record.device_id = device_id
                existing_record.client_version = client_version
                existing_record.confidence_score = confidence_score
                existing_record.created_by = created_by
                existing_record.updated_at = text('now()')
                await db.commit()
                return "UPDATED"
        else:
            # 2. Chưa có bản ghi -> Thêm mới
            new_record = DiemDanh(
                sv_id=sv_id, tkb_tiet_id=tkb_tiet_id, ngay_diem_danh=attend_date,
                trang_thai="Có mặt", vitri=vitri, device_id=device_id,
                client_version=client_version, confidence_score=confidence_score, created_by=created_by
            )
            db.add(new_record)
            await db.commit()
            return "INSERTED"

    except SQLAlchemyError as err:
        await db.rollback()
        print(f"[Attendance Service] DB error: {err}")
        return "ERROR"

async def handle_attendance_frame(
    websocket, tkb_tiet_id: int, payload: dict, db: AsyncSession, giangvien_id: int = None
):
    image_b64 = payload.get("image")
    mode = payload.get("mode", "1")
    date_str = payload.get("date")
    target_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    
    vitri = payload.get("vitri")
    device_id = payload.get("device_id")
    client_version = payload.get("client_version")

    if not image_b64: return

    embeddings = await _get_embedding_list(image_b64, mode)
    recognized: list[dict] = []

    for emb in embeddings:
        match, score = await _find_best_match(emb, db)
        if not match: continue

        sv_id = match.sv_id
        sv = await db.scalar(select(SinhVien).where(SinhVien.id == sv_id))
        if not sv: continue

        save_status = await _save_attendance(
            sv_id=sv_id, tkb_tiet_id=tkb_tiet_id, attend_date=target_date, 
            db=db, vitri=vitri, device_id=device_id, 
            client_version=client_version, confidence_score=score, created_by=giangvien_id
        )
        
        if save_status == "ERROR": continue 

        # Đánh dấu cờ "is_new" để báo cho Client biết thẻ này có phải mới vừa quét không
        is_newly_scanned = save_status in ["INSERTED", "UPDATED"]

        recognized.append({
            "id": str(sv.id),
            "name": f"{sv.hodem} {sv.ten}".strip(),
            "mssv": sv.mssv, 
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": "Có mặt", 
            "score": round(float(score), 2), 
            "vitri": vitri or "Tại lớp",
            "is_new": is_newly_scanned 
        })

    if recognized:
        await websocket.send_text(json.dumps({"status": "success", "students": recognized}))
