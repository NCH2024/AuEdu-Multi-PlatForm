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
    - InsightFace buffalo_s (MobileFaceNet + ArcFace):
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
    embedding: list, db: AsyncSession
) -> tuple[Optional[FaceEmbedding], Optional[float]]:
    """
    Tìm sinh viên có khuôn mặt khớp nhất trong database dùng pgvector.

    Chiến lược:
        - Dùng cosine_distance() của pgvector để đo khoảng cách giữa embedding
          từ frame thời gian thực và tất cả embedding đã lưu trong DB.
        - ORDER BY distance ASC → lấy 1 bản ghi gần nhất.
        - NGƯỠNG AN TOÀN: Nếu khoảng cách ≥ RECOGNITION_THRESHOLD thì
          bắt buộc trả về (None, None) – từ chối nhận diện người lạ.

    Args:
        embedding: Vector 512-D cần tra cứu (đã L2-normalize).
        db: AsyncSession của SQLAlchemy.

    Returns:
        tuple: (FaceEmbedding, cosine_distance) hoặc (None, None) nếu không khớp.
    """
    # Tính biểu thức khoảng cách Cosine (sẽ được pgvector tính trên DB)
    distance_expr = FaceEmbedding.embedding.cosine_distance(embedding)

    stmt = (
        select(FaceEmbedding, distance_expr.label("score"))
        .order_by(distance_expr)  # Khoảng cách nhỏ nhất trước
        .limit(1)                 # Chỉ lấy ứng viên gần nhất
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        # Không có embedding nào trong database (chưa đào tạo sinh viên nào)
        return None, None

    match: FaceEmbedding = row[0]
    score: float = float(row[1])

    # =========================================================================
    # NGƯỠNG AN TOÀN – THRESHOLD GUARD
    # =========================================================================
    # Đây là điều kiện phòng vệ quan trọng nhất: Nếu embedding tốt nhất tìm được
    # vẫn quá xa (khoảng cách ≥ RECOGNITION_THRESHOLD), ta từ chối hoàn toàn.
    # Điều này ngăn hệ thống nhận nhầm người lạ thành sinh viên đã đăng ký.
    if score >= RECOGNITION_THRESHOLD:
        print(
            f"[Attendance Service][Threshold Guard] "
            f"Từ chối nhận diện – Cosine Distance: {score:.4f} ≥ {RECOGNITION_THRESHOLD} (ngưỡng)"
        )
        return None, None

    print(
        f"[Attendance Service] Nhận diện thành công – SV_ID: {match.sv_id}, "
        f"Cosine Distance: {score:.4f} (< {RECOGNITION_THRESHOLD})"
    )
    return match, score


async def _save_attendance(
    sv_id: int,
    tkb_tiet_id: int,
    attend_date: datetime.date,
    db: AsyncSession,
    vitri: Optional[str] = None,
    device_id: Optional[str] = None,
    client_version: Optional[str] = None,
    confidence_score: Optional[float] = None,
    created_by: Optional[int] = None,
) -> str:
    """
    Ghi nhận hoặc cập nhật bản ghi điểm danh trong database.

    Logic:
        - Nếu đã "Có mặt" → Trả về "ALREADY_PRESENT" (idempotent, không ghi đè)
        - Nếu đang "Vắng"  → Cập nhật thành "Có mặt" và trả về "UPDATED"
        - Nếu chưa có bản ghi → Tạo mới và trả về "INSERTED"
        - Nếu lỗi DB       → Rollback và trả về "ERROR"

    Returns:
        str: Một trong "ALREADY_PRESENT", "UPDATED", "INSERTED", "ERROR"
    """
    try:
        # Kiểm tra xem sinh viên này đã có bản ghi điểm danh trong ngày chưa
        existing_stmt = select(DiemDanh).where(
            DiemDanh.sv_id == sv_id,
            DiemDanh.tkb_tiet_id == tkb_tiet_id,
            DiemDanh.ngay_diem_danh == attend_date,
        )
        result = await db.execute(existing_stmt)
        existing_record: Optional[DiemDanh] = result.scalar_one_or_none()

        if existing_record:
            if existing_record.trang_thai == "Có mặt":
                # Đã điểm danh rồi, không làm gì thêm (idempotent)
                return "ALREADY_PRESENT"

            # Trạng thái là "Vắng" → Cho phép cập nhật thành "Có mặt"
            existing_record.trang_thai = "Có mặt"
            existing_record.vitri = vitri
            existing_record.device_id = device_id
            existing_record.client_version = client_version
            existing_record.confidence_score = confidence_score
            existing_record.created_by = created_by
            existing_record.updated_at = text("now()")
            await db.commit()
            return "UPDATED"

        else:
            # Chưa có bản ghi → Tạo mới
            new_record = DiemDanh(
                sv_id=sv_id,
                tkb_tiet_id=tkb_tiet_id,
                ngay_diem_danh=attend_date,
                trang_thai="Có mặt",
                vitri=vitri,
                device_id=device_id,
                client_version=client_version,
                confidence_score=confidence_score,
                created_by=created_by,
            )
            db.add(new_record)
            await db.commit()
            return "INSERTED"

    except SQLAlchemyError as err:
        # Rollback transaction khi gặp lỗi DB
        await db.rollback()
        print(f"[Attendance Service][DB Error] Lỗi ghi điểm danh SV_ID={sv_id}: {err}")
        return "ERROR"


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
    # BƯỚC 3: Xử lý từng embedding tìm được
    # ------------------------------------------------------------------
    recognized: list[dict] = []

    for emb in embeddings:
        # 3a. Tra cứu DB với Threshold Guard
        match, score = await _find_best_match(emb, db)

        # 3b. _find_best_match đã áp dụng Threshold – None nghĩa là không nhận diện được
        if match is None:
            continue

        sv_id: int = match.sv_id

        # 3c. Lấy thông tin sinh viên
        sv: Optional[SinhVien] = await db.scalar(
            select(SinhVien).where(SinhVien.id == sv_id)
        )
        if sv is None:
            print(f"[Attendance Service][WARN] FaceEmbedding tham chiếu đến SV_ID={sv_id} không tồn tại!")
            continue

        # 3d. Ghi nhận điểm danh
        save_status = await _save_attendance(
            sv_id=sv_id,
            tkb_tiet_id=tkb_tiet_id,
            attend_date=target_date,
            db=db,
            vitri=vitri,
            device_id=device_id,
            client_version=client_version,
            confidence_score=round(float(score), 4),
            created_by=giangvien_id,
        )

        if save_status == "ERROR":
            continue

        # 3e. Đánh dấu "is_new" để Client biết đây có phải lần quét đầu tiên không
        #     (INSERTED/UPDATED = mới quét; ALREADY_PRESENT = đã quét trước đó)
        is_newly_scanned: bool = save_status in ("INSERTED", "UPDATED")

        recognized.append({
            "id": sv.id,
            "name": f"{sv.hodem} {sv.ten}".strip(),
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": "Có mặt",
            "score": round(float(score), 4),
            "vitri": vitri or "Tại lớp",
            "is_new": is_newly_scanned,
            "save_status": save_status,  # Để debug/logging phía Client nếu cần
        })

    # ------------------------------------------------------------------
    # BƯỚC 4: Phản hồi về Client nếu có sinh viên được nhận diện
    # ------------------------------------------------------------------
    if recognized:
        await websocket.send_text(
            json.dumps({"status": "success", "students": recognized}, ensure_ascii=False)
        )
