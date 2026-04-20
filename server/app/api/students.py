from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import DiemDanh, TKBTiet, SinhVien, ThoiKhoaBieu
from datetime import datetime, date
from sqlalchemy import or_, cast, String, text, func, case, select, update

router = APIRouter()

def model_to_dict(obj):
    """Chuyển SQLAlchemy model → dict (sử dụng trong mọi router)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

@router.get("/sinhvien")
async def get_danh_sach_sinh_vien(class_id: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(SinhVien)
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