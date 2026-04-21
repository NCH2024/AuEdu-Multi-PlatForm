# server/app/services/attendance_service.py
import json, datetime, asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    sv_id: int,
    tkb_tiet_id: int,
    attend_date: datetime.date,
    db: AsyncSession,
    vitri: str = None,
    device_id: str = None,
    client_version: str = None,
    confidence_score: float = None,
    created_by: int = None
):
    """
    Dùng INSERT ... ON CONFLICT DO NOTHING để triệt tiêu hoàn toàn Race Condition.
    """
    stmt = pg_insert(DiemDanh).values(
        sv_id=sv_id,
        tkb_tiet_id=tkb_tiet_id,
        ngay_diem_danh=attend_date,
        trang_thai="Có mặt",
        vitri=vitri,
        device_id=device_id,
        client_version=client_version,
        confidence_score=confidence_score,
        created_by=created_by
    )
    
    # Nếu trùng cặp (sv_id, tkb_tiet_id, ngày) thì bỏ qua không báo lỗi
    stmt = stmt.on_conflict_do_nothing(
        constraint='uq_diemdanh_sv_tiet_ngay'
    )
    
    try:
        # Sử dụng transaction an toàn
        result = await db.execute(stmt)
        await db.commit()
        # rowcount > 0 nghĩa là đã insert mới. = 0 nghĩa là bị trùng nên đã bỏ qua.
        return result.rowcount > 0 
    except SQLAlchemyError as err:
        await db.rollback()
        print(f"[Attendance Service] DB error: {err}")
        return False


async def handle_attendance_frame(
    websocket,
    tkb_tiet_id: int,
    payload: dict,
    db: AsyncSession,
    giangvien_id: int = None # Thêm params nhận từ người dùng đã xác thực
):
    image_b64 = payload.get("image")
    mode = payload.get("mode", "1")
    date_str = payload.get("date")
    target_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    
    # Lấy thêm các tham số thiết bị, vị trí từ client gửi lên
    vitri = payload.get("vitri")
    device_id = payload.get("device_id")
    client_version = payload.get("client_version")

    if not image_b64:
        return

    embeddings = await _get_embedding_list(image_b64, mode)
    recognized: list[dict] = []

    for emb in embeddings:
        match, score = await _find_best_match(emb, db)
        if not match:
            continue
            
        # Có thể thêm logic kiểm tra ngưỡng (threshold) tại đây
        # Ví dụ: if score > 0.4: continue (khoảng cách càng lớn càng không giống)

        sv_id = match.sv_id
        sv = await db.scalar(select(SinhVien).where(SinhVien.id == sv_id))
        if not sv:
            continue

        saved = await _save_attendance(
            sv_id=sv_id, 
            tkb_tiet_id=tkb_tiet_id, 
            attend_date=target_date, 
            db=db,
            vitri=vitri,
            device_id=device_id,
            client_version=client_version,
            confidence_score=score,
            created_by=giangvien_id
        )
        
        if not saved:
            continue # Đã điểm danh trước đó hoặc lỗi

        recognized.append({
            "id": str(sv.id),
            "name": f"{sv.hodem} {sv.ten}".strip(),
            "mssv": sv.mssv, # Bổ sung thêm để Card hiển thị mã số
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": "Có mặt", 
            "score": round(float(score), 2), 
            "vitri": vitri or "Tại lớp"
        })

    if recognized:
        await websocket.send_text(json.dumps({"status": "success", "students": recognized}))
