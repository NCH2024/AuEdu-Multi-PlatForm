from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, cast, String, text, func, case, update
from app.db.session import get_db
from app.db.models import DiemDanh, TKBTiet, SinhVien, ThoiKhoaBieu
from app.core.security import get_current_user_id
from app.core.audit import log_audit
from datetime import datetime, date
from typing import List, Optional

router = APIRouter()

def model_to_dict(obj):
    """Chuyển SQLAlchemy model → dict (sử dụng trong mọi router)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

@router.get("/sinhvien")
async def get_danh_sach_sinh_vien(class_id: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(SinhVien).where(SinhVien.deleted_at.is_(None))
    if class_id and class_id.startswith("eq."):
        c_id = class_id.replace("eq.", "")
        stmt = stmt.where(SinhVien.class_id == c_id)
    result = await db.execute(stmt)
    res = []
    for sv in result.scalars().all():
        d = model_to_dict(sv)
        d["ngaysinh"] = str(d["ngaysinh"]) if d.get("ngaysinh") else None
        d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
        res.append(d)
    return res

@router.get("/search-students")
async def search_global_students(gv_id: int, keyword: str, db: AsyncSession = Depends(get_db)):
    # 1. Tìm tất cả các lớp (lop_id) mà Giảng viên này đang dạy
    tkb_stmt = select(ThoiKhoaBieu.lop_id).where(ThoiKhoaBieu.giangvien_id == gv_id)
    res_tkb = await db.execute(tkb_stmt)
    lop_ids = [row for row in res_tkb.scalars().all()]

    if not lop_ids:
        return [] # Nếu GV chưa dạy lớp nào thì trả về rỗng

    search_pattern = f"%{keyword.strip()}%"

    # 2. Tìm sinh viên thuộc các lớp đó khớp với từ khóa (Theo MSSV hoặc Tên/Họ đệm)
    from app.db.models import Lop
    stmt = (
        select(SinhVien, Lop.tenlop)
        .join(Lop, SinhVien.class_id == Lop.id)
        .where(SinhVien.deleted_at.is_(None))
        .where(SinhVien.class_id.in_(lop_ids))
        .where(
            or_(
                cast(SinhVien.id, String).ilike(search_pattern),
                SinhVien.ten.ilike(search_pattern),
                SinhVien.hodem.ilike(search_pattern)
            )
        )
        .limit(20) # Giới hạn 20 kết quả để tránh nghẽn mạng nếu gõ từ khóa quá chung chung (VD: "Nguyễn")
    )
    
    res = await db.execute(stmt)
    
    data = []
    for sv_obj, ten_lop in res.all():
        sv_dict = model_to_dict(sv_obj)
        sv_dict['ten_lop'] = ten_lop # Đính kèm tên lớp để giao diện hiển thị cho rõ
        
        # Format lại ngày sinh cho đẹp
        if sv_dict.get('ngaysinh'):
            sv_dict['ngaysinh'] = sv_dict['ngaysinh'].strftime("%d/%m/%Y")
            
        data.append(sv_dict)
        
    return data

@router.get("/student/{sv_id}/history")
async def get_student_personal_history(sv_id: int, gv_id: int, db: AsyncSession = Depends(get_db)):
    from app.db.models import HocPhan, ThoiKhoaBieu, DiemDanh, TKBTiet
    
    # Truy vấn: Lấy lịch sử và kèm theo 'sobuoi' của môn học đó
    stmt = (
        select(
            DiemDanh.ngay_diem_danh, 
            DiemDanh.trang_thai, 
            DiemDanh.created_at,
            TKBTiet.phong_hoc,
            HocPhan.tenhocphan,
            HocPhan.sobuoi # Lấy tổng số buổi thiết lập
        )
        .join(TKBTiet, DiemDanh.tkb_tiet_id == TKBTiet.id)
        .join(ThoiKhoaBieu, TKBTiet.tkb_id == ThoiKhoaBieu.id)
        .join(HocPhan, ThoiKhoaBieu.hocphan_id == HocPhan.id)
        .where(DiemDanh.sv_id == sv_id)
        .where(ThoiKhoaBieu.giangvien_id == gv_id)
        .order_by(DiemDanh.ngay_diem_danh.desc())
    )
    
    res = await db.execute(stmt)
    data = []
    for row in res.all():
        data.append({
            "ngay": row.ngay_diem_danh.strftime("%d/%m/%Y") if row.ngay_diem_danh else "N/A",
            "trang_thai": row.trang_thai,
            "gio_quet": row.created_at.strftime("%H:%M:%S") if row.created_at else "--:--",
            "phong_hoc": row.phong_hoc,
            "ten_mon": row.tenhocphan,
            "tong_so_buoi": row.sobuoi # Đưa dữ liệu này về Frontend
        })
    return data

# --- ADMIN CRUD ---

from pydantic import BaseModel
from typing import Optional, List

class StudentCreate(BaseModel):
    """Schema tạo sinh viên mới — id là MSSV."""
    id: int # MSSV
    ma_ho_so: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    hodem: str
    ten: str
    gioitinh: str
    ngaysinh: Optional[date] = None
    noi_sinh: Optional[str] = None
    dan_toc: Optional[str] = None
    ton_giao: Optional[str] = None
    nguyen_quan: Optional[str] = None
    ho_khau: Optional[str] = None
    ngay_vao_doan: Optional[date] = None
    class_id: str
    bac_dao_tao: Optional[str] = None
    ho_ten_cha: Optional[str] = None
    nghe_nghiep_cha: Optional[str] = None
    ho_ten_me: Optional[str] = None
    nghe_nghiep_me: Optional[str] = None
    dien_thoai: Optional[str] = None
    trang_thai: Optional[str] = "Đang học"
    ngay_ra_quyet_dinh: Optional[date] = None
    diachi: Optional[str] = None
    ghichu: Optional[str] = None

class StudentUpdate(BaseModel):
    ma_ho_so: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    hodem: Optional[str] = None
    ten: Optional[str] = None
    gioitinh: Optional[str] = None
    ngaysinh: Optional[date] = None
    noi_sinh: Optional[str] = None
    dan_toc: Optional[str] = None
    ton_giao: Optional[str] = None
    nguyen_quan: Optional[str] = None
    ho_khau: Optional[str] = None
    ngay_vao_doan: Optional[date] = None
    class_id: Optional[str] = None
    bac_dao_tao: Optional[str] = None
    ho_ten_cha: Optional[str] = None
    nghe_nghiep_cha: Optional[str] = None
    ho_ten_me: Optional[str] = None
    nghe_nghiep_me: Optional[str] = None
    dien_thoai: Optional[str] = None
    trang_thai: Optional[str] = None
    ngay_ra_quyet_dinh: Optional[date] = None
    diachi: Optional[str] = None
    ghichu: Optional[str] = None

class StudentBatch(BaseModel):
    items: List[StudentCreate]

@router.post("/")
async def create_student(
    sv: StudentCreate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_sv = SinhVien(**sv.model_dump())
    db_sv.created_by = current_user_id
    db_sv.updated_by = current_user_id
    db.add(db_sv)
    await db.commit()
    await db.refresh(db_sv)
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="CREATE",
        entity="SinhVien",
        entity_id=db_sv.id,
        details=sv.model_dump(),
        request=request
    )
    await db.commit()

    return {"id": db_sv.id, "message": "Created successfully"}

from sqlalchemy.dialects.postgresql import insert as pg_insert

@router.post("/batch")
async def create_students_batch(
    batch: StudentBatch, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Tạo nhiều sinh viên cùng lúc (Báo lỗi nếu trùng MSSV)."""
    if not batch.items:
        return {"message": "Không có dữ liệu", "count": 0}
    
    # 1. Kiểm tra các ID đã tồn tại
    ids = [item.id for item in batch.items]
    stmt_check = select(SinhVien.id).where(SinhVien.id.in_(ids))
    res_check = await db.execute(stmt_check)
    existing_ids = set(res_check.scalars().all())
    
    if existing_ids:
        return {
            "error": "DUPLICATE_MSSV",
            "message": f"Có {len(existing_ids)} sinh viên đã tồn tại trong hệ thống.",
            "duplicate_ids": list(existing_ids)
        }
    
    # 2. Nếu không trùng, tiến hành INSERT
    data = []
    for item in batch.items:
        d = item.model_dump()
        d["created_by"] = current_user_id
        d["updated_by"] = current_user_id
        data.append(d)
        
    stmt = pg_insert(SinhVien).values(data)
    
    result = await db.execute(stmt)
    await db.commit()
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="BATCH_CREATE",
        entity="SinhVien",
        details={"count": result.rowcount, "ids": ids},
        request=request
    )
    await db.commit()
    
    return {
        "message": f"Thêm mới thành công {result.rowcount} sinh viên.",
        "count": result.rowcount
    }

@router.put("/{id}")
async def update_student(
    id: int, 
    sv: StudentUpdate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_sv = await db.get(SinhVien, id)
    if not db_sv:
        raise HTTPException(status_code=404, detail="Student not found")
    for k, v in sv.model_dump(exclude_unset=True).items():
        setattr(db_sv, k, v)
    
    db_sv.updated_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="UPDATE",
        entity="SinhVien",
        entity_id=id,
        details=sv.model_dump(exclude_unset=True),
        request=request
    )
    
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_student(
    id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Xóa sinh viên theo ID hệ thống."""
    db_sv = await db.get(SinhVien, id)
    if not db_sv or db_sv.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Soft delete
    db_sv.deleted_at = datetime.now()
    db_sv.deleted_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="DELETE",
        entity="SinhVien",
        entity_id=id,
        request=request
    )
    
    await db.commit()
    return {"message": "Deleted successfully"}