"""
server/app/services/attendance_service.py
==========================================
Dịch vụ Điểm Danh (Attendance Service)

Chịu trách nhiệm:
    1. Gọi AI Engine để trích xuất embedding từ frame camera.
    2. Tra cứu sinh viên khớp nhất trong DB dùng pgvector Cosine Distance.
    3. NGƯỠNG AN TOÀN (Threshold Guard): Từ chối người lạ nếu khoảng cách vượt ngưỡng.
    4. Ghi nhận bản ghi điểm danh và trả kết quả về WebSocket.

Về Threshold (Ngưỡng Nhận diện):
    - pgvector cosine_distance trả về giá trị trong [0.0, 2.0]:
        * 0.0 = giống hệt nhau (cùng người, cùng ảnh)
        * 1.0 = vuông góc (không tương quan)
        * 2.0 = ngược chiều hoàn toàn
    - InsightFace buffalo_s (ArcFace 512-D):
        * Cùng người    → cosine_distance thường < 0.40
        * Khác người    → cosine_distance thường > 0.55
        * Vùng "mơ hồ" → 0.40 – 0.55
    - Ta chọn THRESHOLD = 0.45 (bảo thủ): Từ chối tất cả embedding có
      khoảng cách ≥ 0.45 để tránh false positive (nhận nhầm người lạ).
    - Có thể điều chỉnh RECOGNITION_THRESHOLD tùy môi trường thực tế.

Tác giả: AuEdu Senior AI Team
"""

import json
import asyncio
import datetime
from typing import Optional

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import SinhVien, DiemDanh, FaceEmbedding
from app.ai.engine import face_engine
from app.core.broadcaster import broadcaster
from app.core.audit import log_audit
from app.services.attendance_cache import attendance_cache
from sqlalchemy.dialects.postgresql import insert


# ==============================================================================
# HẰNG SỐ CẤU HÌNH NHẬN DIỆN
# ==============================================================================

# Ngưỡng khoảng cách Cosine tối đa để chấp nhận là "cùng người"
# Giá trị nhỏ hơn → Nghiêm ngặt hơn (ít false positive, nhiều false negative)
# Giá trị lớn hơn → Dễ chấp nhận hơn (nhiều false positive, ít false negative)
RECOGNITION_THRESHOLD: float = 0.45


# ==============================================================================
# PRIVATE HELPER FUNCTIONS
# ==============================================================================

async def _get_embeddings_from_frame(image_b64: str, mode: str) -> list:
    """
    Gọi AI Engine (chạy đồng bộ nặng) trong một thread riêng biệt bằng
    asyncio.to_thread() để không chặn event loop của FastAPI/WebSocket.

    Args:
        image_b64: Chuỗi Base64 của frame camera.
        mode: "1" (1 người) hoặc "all" (toàn lớp).

    Returns:
        list[list[float]]: Danh sách embedding 512-D.
    """
    # asyncio.to_thread: Chạy hàm CPU-intensive trong ThreadPoolExecutor,
    # giải phóng event loop để tiếp tục xử lý các coroutine khác.
    return await asyncio.to_thread(face_engine.process_attendance_frame, image_b64, mode)


async def _find_best_match(
    tkb_tiet_id: int, embedding: list, db: AsyncSession
) -> tuple[Optional[dict], Optional[float]]:
    """
    Tìm sinh viên khớp nhất. Thử tìm trong Cache trước, nếu không có hoặc lỗi thì fallback DB.
    """
    # 1. Thử In-Memory Cache (siêu tốc)
    match, score = attendance_cache.find_best_match(tkb_tiet_id, embedding, RECOGNITION_THRESHOLD)
    
    # Nếu score != -1.0, tức là Cache đã được tải thành công
    if score is not None and score != -1.0:
        if match is None:
            # Có trong cache nhưng vượt ngưỡng, từ chối nhận diện
            print(
                f"[Attendance Service][Threshold Guard] "
                f"Từ chối nhận diện (Cache) – Cosine Distance: {score:.4f} ≥ {RECOGNITION_THRESHOLD}"
            )
        else:
            print(
                f"[Attendance Service] Nhận diện thành công (Cache) – SV_ID: {match['id']}, "
                f"Cosine Distance: {score:.4f} (< {RECOGNITION_THRESHOLD})"
            )
        return match, score

    # 2. Fallback Truy vấn DB (chậm hơn) - Chỉ chạy khi Cache hoàn toàn trống (score == -1.0)
    distance_expr = FaceEmbedding.embedding.cosine_distance(embedding)
    stmt = (
        select(FaceEmbedding, distance_expr.label("score"))
        .order_by(distance_expr)
        .limit(1)
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        return None, None

    db_match: FaceEmbedding = row[0]
    db_score: float = float(row[1])

    if db_score >= RECOGNITION_THRESHOLD:
        print(
            f"[Attendance Service][Threshold Guard] "
            f"Từ chối nhận diện (Fallback) – Cosine Distance: {db_score:.4f} ≥ {RECOGNITION_THRESHOLD}"
        )
        return None, None

    # Lấy thông tin SinhVien
    sv = await db.scalar(select(SinhVien).where(SinhVien.id == db_match.sv_id))
    if sv:
        print(
            f"[Attendance Service] Nhận diện thành công (Fallback DB) – SV_ID: {sv.id}, "
            f"Cosine Distance: {db_score:.4f}"
        )
        return {"id": sv.id, "hodem": sv.hodem, "ten": sv.ten}, db_score
        
    return None, None


async def bulk_upsert_attendance(
    recognitions: list[dict],
    tkb_tiet_id: int,
    attend_date: datetime.date,
    db: AsyncSession,
    created_by: Optional[int] = None,
) -> dict[int, str]:
    """
    Ghi nhận hoặc cập nhật hàng loạt bản ghi điểm danh trong database.
    Sử dụng INSERT ... ON CONFLICT DO UPDATE để giảm thiểu truy vấn.
    """
    if not recognitions:
        return {}

    sv_ids = [r["sv_id"] for r in recognitions]
    scores = {r["sv_id"]: r["score"] for r in recognitions}
    vitris = {r["sv_id"]: r["vitri"] for r in recognitions}
    device_ids = {r["sv_id"]: r["device_id"] for r in recognitions}
    client_versions = {r["sv_id"]: r["client_version"] for r in recognitions}

    try:
        # 1. Fetch trạng thái hiện tại để phân loại (chỉ mất 1 query cho cả danh sách)
        existing_stmt = select(DiemDanh).where(
            DiemDanh.tkb_tiet_id == tkb_tiet_id,
            DiemDanh.ngay_diem_danh == attend_date,
            DiemDanh.sv_id.in_(sv_ids)
        )
        existing_records = (await db.scalars(existing_stmt)).all()
        existing_map = {r.sv_id: r for r in existing_records}

        status_map = {}
        to_upsert = []

        for sv_id in sv_ids:
            existing = existing_map.get(sv_id)
            if existing and existing.trang_thai == "Có mặt":
                status_map[sv_id] = "ALREADY_PRESENT"
                continue

            if existing:
                status_map[sv_id] = "UPDATED"
            else:
                status_map[sv_id] = "INSERTED"

            to_upsert.append({
                "sv_id": sv_id,
                "tkb_tiet_id": tkb_tiet_id,
                "ngay_diem_danh": attend_date,
                "trang_thai": "Có mặt",
                "vitri": vitris.get(sv_id),
                "device_id": device_ids.get(sv_id),
                "client_version": client_versions.get(sv_id),
                "confidence_score": scores.get(sv_id),
                "created_by": created_by,
            })

        # 2. Bulk Upsert vào DB
        if to_upsert:
            stmt = insert(DiemDanh).values(to_upsert)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_diemdanh_sv_tiet_ngay",
                set_={
                    "trang_thai": stmt.excluded.trang_thai,
                    "vitri": stmt.excluded.vitri,
                    "device_id": stmt.excluded.device_id,
                    "client_version": stmt.excluded.client_version,
                    "confidence_score": stmt.excluded.confidence_score,
                    "updated_at": text("now()"),
                }
            )
            await db.execute(stmt)
            # Lưu ý: Không commit ở đây, sẽ commit 1 lần duy nhất ở hàm gọi (handle_attendance_frame)

        return status_map

    except SQLAlchemyError as err:
        print(f"[Attendance Service][CRITICAL] Lỗi Bulk Upsert: {err}")
        return {sv_id: "ERROR" for sv_id in sv_ids}


# ==============================================================================
# PUBLIC ENTRY POINT – Được gọi bởi WebSocket Consumer
# ==============================================================================

async def handle_attendance_frame(
    websocket: WebSocket,
    tkb_tiet_id: int,
    payload: dict,
    db: AsyncSession,
    giangvien_id: Optional[int] = None,
) -> None:
    """
    Xử lý một frame điểm danh nhận được từ WebSocket Consumer.

    Luồng chính:
        1. Giải mã payload → Trích xuất tham số
        2. Gọi AI Engine để lấy danh sách embedding (trong thread riêng)
        3. Với mỗi embedding:
            a. Tra cứu DB tìm sinh viên khớp nhất (có Threshold Guard)
            b. Nếu khớp → Ghi nhận điểm danh
            c. Nếu không khớp → Bỏ qua (không phản hồi về người lạ)
        4. Gửi danh sách sinh viên đã nhận diện về Client qua WebSocket

    Args:
        websocket: WebSocket connection đang hoạt động.
        tkb_tiet_id: ID tiết thời khoá biểu cần điểm danh.
        payload: Dữ liệu JSON nhận từ Client {"image", "mode", "date", ...}
        db: AsyncSession của SQLAlchemy.
        giangvien_id: ID giảng viên phụ trách tiết học (dùng cho audit trail).
    """
    # ------------------------------------------------------------------
    # BƯỚC 1: Giải mã payload
    # ------------------------------------------------------------------
    image_b64: Optional[str] = payload.get("image")
    mode: str = payload.get("mode", "1")
    date_str: Optional[str] = payload.get("date")
    vitri: Optional[str] = payload.get("vitri")
    device_id: Optional[str] = payload.get("device_id")
    client_version: Optional[str] = payload.get("client_version")

    # Nếu không có ảnh → Không làm gì
    if not image_b64:
        return

    # Xác định ngày điểm danh (dùng ngày hôm nay nếu Client không gửi)
    try:
        target_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    except ValueError:
        target_date = datetime.date.today()

    # ------------------------------------------------------------------
    # BƯỚC 2: Gọi AI Engine để trích xuất embedding
    #         (asyncio.to_thread() giúp không block event loop)
    # ------------------------------------------------------------------
    embeddings: list = await _get_embeddings_from_frame(image_b64, mode)

    if not embeddings:
        # Không phát hiện được khuôn mặt nào đủ chất lượng → Bỏ qua frame này
        return

    # ------------------------------------------------------------------
    # BƯỚC 3: Tra cứu đồng thời các embedding (Parallel Processing)
    # ------------------------------------------------------------------
    async def process_embedding(emb):
        sv_dict, score = await _find_best_match(tkb_tiet_id, emb, db)
        if sv_dict:
            return {
                "sv_id": sv_dict["id"],
                "sv": sv_dict,
                "score": score,
                "vitri": vitri,
                "device_id": device_id,
                "client_version": client_version
            }
        return None

    # Chạy song song tìm kiếm
    match_results = await asyncio.gather(*(process_embedding(emb) for emb in embeddings))
    valid_matches = [res for res in match_results if res is not None]

    if not valid_matches:
        return

    # ------------------------------------------------------------------
    # BƯỚC 4: Ghi dữ liệu hàng loạt (Bulk Upsert)
    # ------------------------------------------------------------------
    status_map = await bulk_upsert_attendance(
        recognitions=valid_matches,
        tkb_tiet_id=tkb_tiet_id,
        attend_date=target_date,
        db=db,
        created_by=giangvien_id,
    )

    # ------------------------------------------------------------------
    # BƯỚC 5: Xử lý Audit Log và Response
    # ------------------------------------------------------------------
    recognized: list[dict] = []

    for match in valid_matches:
        sv = match["sv"]
        sv_id = match["sv_id"]
        score = match["score"]
        save_status = status_map.get(sv_id, "ERROR")

        if save_status == "ERROR":
            continue

        # --- AUDIT LOG: RECOGNITION ---
        if save_status in ("INSERTED", "UPDATED"):
            await log_audit(
                db=db,
                user_id=giangvien_id,
                action="RECOGNITION",
                entity="SinhVien",
                entity_id=str(sv_id),
                details={
                    "tkb_tiet_id": tkb_tiet_id,
                    "date": str(target_date),
                    "score": round(float(score), 4),
                    "vitri": vitri,
                    "save_status": save_status
                },
                request=None
            )

        is_newly_scanned: bool = save_status in ("INSERTED", "UPDATED")

        recognized.append({
            "id": sv["id"],
            "name": f"{sv['hodem']} {sv['ten']}".strip(),
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": "Có mặt",
            "score": round(float(score), 4),
            "vitri": vitri or "Tại lớp",
            "is_new": is_newly_scanned,
            "save_status": save_status,
        })

    # Commit 1 lần duy nhất cho toàn bộ frame (kể cả audit_log và diemdanh)
    try:
        await db.commit()
    except SQLAlchemyError as err:
        await db.rollback()
        print(f"[Attendance Service][CRITICAL] Lỗi commit DB cho frame: {err}")
        return

    # ------------------------------------------------------------------
    # BƯỚC 4: Phản hồi về Client nếu có sinh viên được nhận diện
    # ------------------------------------------------------------------
    if recognized:
        # Gửi phản hồi cho Client (giảng viên) đang thực hiện điểm danh
        response = {"status": "success", "students": recognized}
        await websocket.send_text(
            json.dumps(response, ensure_ascii=False)
        )
        
        # Broadcast cho Admin để giám sát thời gian thực
        # Thêm thông tin bổ sung nếu cần (ví dụ: tên môn học, lớp - nhưng hiện tại ta chỉ gửi student info)
        await broadcaster.broadcast({
            "type": "attendance_update",
            "data": recognized
        })
