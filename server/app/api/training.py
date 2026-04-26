# server/app/api/training.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, cast, String, text
from sqlalchemy.dialects.postgresql import insert
from typing import List
from app.db.session import get_db
from app.db.models import (
    Lop, ThoiKhoaBieu, SinhVien,
    FaceEmbedding, GiangVien,
)
from pydantic import BaseModel
from app.ai.engine import face_engine

router = APIRouter()


class FaceEnrollRequest(BaseModel):
    sv_id: int
    gv_id: int
    images: List[str]   # base64 string list


# -------------------------------------------------
# 1. Lớp giảng viên dạy
# -------------------------------------------------
@router.get("/giangvien/{gv_id}/lophoc")
async def get_lop_giang_day(gv_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Lop)
        .join(ThoiKhoaBieu, Lop.id == ThoiKhoaBieu.lop_id)
        .where(
            ThoiKhoaBieu.giangvien_id == gv_id,
            ThoiKhoaBieu.deleted_at.is_(None),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return [
        {"id": lop.id, "name": lop.tenlop, "siso": 0}   # siso có thể tính later
        for lop in result.scalars().all()
    ]


# -------------------------------------------------
# 2. Danh sách sinh viên lớp + trạng thái dữ liệu khuôn mặt
# -------------------------------------------------
@router.get("/lop/{class_id}/sinhvien")
async def get_sinhvien_training(class_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(SinhVien, FaceEmbedding.sv_id)
        .outerjoin(FaceEmbedding, SinhVien.id == FaceEmbedding.sv_id)
        .where(
            SinhVien.class_id == class_id,
            SinhVien.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    data = []
    for sv, face_id in result:
        data.append(
            {
                "id": sv.id,
                "name": f"{sv.hodem} {sv.ten}".strip(),
                "has_data": bool(face_id is not None),
            }
        )
    return data


# -------------------------------------------------
# 3. Tìm kiếm sinh viên trong các lớp GV quản lý
# -------------------------------------------------
@router.get("/giangvien/{gv_id}/timkiem")
async def search_sinhvien(gv_id: int, keyword: str, db: AsyncSession = Depends(get_db)):
    # Lấy danh sách lớp GV dạy
    lop_stmt = (
        select(ThoiKhoaBieu.lop_id)
        .where(
            ThoiKhoaBieu.giangvien_id == gv_id,
            ThoiKhoaBieu.deleted_at.is_(None),
        )
        .distinct()
    )
    lop_res = await db.execute(lop_stmt)
    lop_ids = [row for row in lop_res.scalars().all()]
    if not lop_ids:
        return []

    kw = f"%{keyword}%"
    stmt = (
        select(SinhVien, FaceEmbedding.sv_id)
        .outerjoin(FaceEmbedding, SinhVien.id == FaceEmbedding.sv_id)
        .where(
            SinhVien.class_id.in_(lop_ids),
            SinhVien.deleted_at.is_(None),
            or_(
                cast(SinhVien.id, String).ilike(kw),
                SinhVien.ten.ilike(kw),
                SinhVien.hodem.ilike(kw),
            ),
        )
    )
    result = await db.execute(stmt)
    data = []
    for sv, face_id in result:
        data.append(
            {
                "id": sv.id,
                "class_id": sv.class_id,
                "name": f"{sv.hodem} {sv.ten}".strip(),
                "has_data": bool(face_id is not None),
            }
        )
    return data


# -------------------------------------------------
# 4. Đăng ký / cập nhật dữ liệu khuôn mặt (UPSERT)
# -------------------------------------------------
@router.post("/face/enroll")
async def enroll_face_data(
    req: FaceEnrollRequest, db: AsyncSession = Depends(get_db)
):
    try:
        # Lấy embedding trung bình từ AI
        fused = face_engine.extract_fused_embedding(req.images)

        # RÀ SOÁT TRÙNG LẶP (DUPLICATE CHECK)
        # Giới hạn cosine_distance. Khoảng cách < 0.35 thường được coi là cùng 1 người.
        threshold = 0.001 
        distance = FaceEmbedding.embedding.cosine_distance(fused)
        
        check_stmt = (
            select(FaceEmbedding.sv_id, distance.label('score'))
            .where(FaceEmbedding.sv_id != req.sv_id) # Bỏ qua data cũ của chính nó (nếu sinh viên này cập nhật lại mặt)
            .order_by(distance)
            .limit(1)
        )
        
        check_res = await db.execute(check_stmt)
        match = check_res.first()
        
        if match and match.score < threshold:
            # Nếu tìm thấy một vector quá sát
            raise ValueError(f"Hệ thống phát hiện khuôn mặt này TRÙNG LẶP với dữ liệu của Sinh viên ID {match.sv_id} (Độ lệch {match.score:.2f}). Vui lòng kiểm tra lại sinh viên!")

        # Không trùng lặp -> UPSERT vào bảng FaceEmbedding bình thường
        stmt = insert(FaceEmbedding).values(
            sv_id=req.sv_id,
            embedding=fused,
            trained_by=req.gv_id,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["sv_id"],
            set_={
                "embedding": fused,
                "trained_by": req.gv_id,
                "updated_at": text("now()"),
                "model_version": "mobilefacenet_model_best.pth"
            },
        )
        await db.execute(stmt)
        await db.commit()
        return {"status": "success", "message": "Cập nhật dữ liệu khuôn mặt thành công!"}
    except ValueError as ve:
        # Lỗi mình tự raise sẽ bay ra đây, trả về 400 Client Error
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"[API Enroll Lỗi] {e}")
        raise HTTPException(
            status_code=500,
            detail="Lỗi hệ thống khi xử lý dữ liệu khuôn mặt.",
        )
