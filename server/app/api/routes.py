# Server_Core/app/api/routes.py
import os
import httpx
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
import base64
import cv2
import numpy as np
from app.ai.engine import face_engine 

from app.db.session import get_db
from app.db.models import SinhVien, ThoiKhoaBieu, TKBTiet, DiemDanh, ThongBao, Lop, HocPhan, HocKy, Tiet, TuanHoc, GiangVien, Khoa

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def model_to_dict(model_obj):
    return {c.name: getattr(model_obj, c.name) for c in model_obj.__table__.columns}

# ---------------------------------------------------------
# 1. API ĐĂNG NHẬP (Proxy chuyển tiếp lên Supabase)
# ---------------------------------------------------------
@router.post("/auth/v1/token")
async def login_proxy(request: Request):
    """Giả lập endpoint đăng nhập của Supabase để App không bị lỗi"""
    body = await request.json()
    grant_type = request.query_params.get("grant_type", "password")
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type={grant_type}",
            json=body,
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
        )
        # Trả về y nguyên kết quả (kể cả lỗi sai mật khẩu hay thành công)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=res.json())
        return res.json()

# ---------------------------------------------------------
# 2. API QUẢN LÝ GIẢNG VIÊN (Lồng tên Khoa)
# ---------------------------------------------------------
@router.get("/giangvien")
async def get_giangvien(id: str = None, auth_id: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(GiangVien, Khoa).outerjoin(Khoa, GiangVien.khoa_id == Khoa.id)
    
    # Client tìm theo ID (Ví dụ: id=eq.3)
    if id and id.startswith("eq."):
        gv_id = int(id.replace("eq.", ""))
        stmt = stmt.where(GiangVien.id == gv_id)
        
    # Client tìm theo Auth UUID sau khi đăng nhập
    if auth_id and auth_id.startswith("eq."):
        a_id = auth_id.replace("eq.", "")
        stmt = stmt.where(GiangVien.auth_id == a_id)
        
    result = await db.execute(stmt)
    res = []
    for gv, khoa in result:
        d = model_to_dict(gv)
        d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
        d["khoa"] = {"tenkhoa": khoa.tenkhoa} if khoa else None
        res.append(d)
    return res

# ---------------------------------------------------------
# 3. API TUẦN HỌC
# ---------------------------------------------------------
@router.get("/tuan_hoc")
async def get_tuan_hoc(db: AsyncSession = Depends(get_db)):
    stmt = select(TuanHoc).order_by(TuanHoc.id.asc())
    result = await db.execute(stmt)
    res = []
    for t in result.scalars().all():
        d = model_to_dict(t)
        d["ngay_bat_dau"] = str(d["ngay_bat_dau"]) if d.get("ngay_bat_dau") else None
        d["ngay_ket_thuc"] = str(d["ngay_ket_thuc"]) if d.get("ngay_ket_thuc") else None
        res.append(d)
    return res

# ---------------------------------------------------------
# 4. API SINH VIÊN
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 5. CÁC API CŨ (Thông báo, TKB, Tiết, Điểm danh)
# ---------------------------------------------------------
@router.get("/thongbao")
async def get_thongbao(limit: int = 3, db: AsyncSession = Depends(get_db)):
    stmt = select(ThongBao).order_by(ThongBao.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    res = []
    for t in result.scalars().all():
        d = model_to_dict(t)
        d["created_at"] = str(t.created_at) if t.created_at else None
        res.append(d)
    return res

# ---------------------------------------------------------
# API THỜI KHÓA BIỂU
# ---------------------------------------------------------
@router.get("/thoikhoabieu")
async def get_thoi_khoa_bieu(giangvien_id: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(ThoiKhoaBieu, Lop, HocPhan, HocKy)\
        .outerjoin(Lop, ThoiKhoaBieu.lop_id == Lop.id)\
        .outerjoin(HocPhan, ThoiKhoaBieu.hocphan_id == HocPhan.id)\
        .outerjoin(HocKy, ThoiKhoaBieu.hocky_id == HocKy.id)
        
    if giangvien_id and giangvien_id.startswith("eq."):
        gv_id = int(giangvien_id.replace("eq.", ""))
        stmt = stmt.where(ThoiKhoaBieu.giangvien_id == gv_id)
        
    result = await db.execute(stmt)
    res = []
    for tkb, lop, hocphan, hocky in result:
        # Lấy TOÀN BỘ các trường gốc của bảng thoikhoabieu (kể cả hocphan_id, lop_id...)
        d = model_to_dict(tkb)
        
        # Nhồi thêm các Object lồng nhau vào
        d["lop"] = {"tenlop": lop.tenlop} if lop else None
        d["hocphan"] = {"tenhocphan": hocphan.tenhocphan, "sobuoi": hocphan.sobuoi} if hocphan else None
        d["hocky"] = {"namhoc": hocky.namhoc, "tenhocky": hocky.tenhocky} if hocky else None
        
        res.append(d)
    return res

# ---------------------------------------------------------
# API TIẾT HỌC
# ---------------------------------------------------------
@router.get("/tkb_tiet")
async def get_tkb_tiet(tkb_id: str = None, thu: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(TKBTiet, Tiet).outerjoin(Tiet, TKBTiet.tiet_id == Tiet.id)
    
    if tkb_id and tkb_id.startswith("in."):
        ids_str = tkb_id.replace("in.(", "").replace(")", "")
        ids = [int(i) for i in ids_str.split(",") if i.strip()]
        stmt = stmt.where(TKBTiet.tkb_id.in_(ids))
        
    if thu and thu.startswith("eq."):
        thu_val = int(thu.replace("eq.", ""))
        stmt = stmt.where(TKBTiet.thu == thu_val)
        
    stmt = stmt.order_by(Tiet.thoigianbd.asc())
        
    result = await db.execute(stmt)
    res = []
    for tkbtiet, tiet in result:
        # Lấy TOÀN BỘ các trường gốc của bảng tkb_tiet (Bao gồm id, tkb_id, tiet_id, thu...)
        d = model_to_dict(tkbtiet)
        d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
        
        # Nhồi thêm chi tiết thời gian của tiết học
        d["tiet"] = {
            "thoigianbd": str(tiet.thoigianbd) if tiet.thoigianbd else None, 
            "thoigiankt": str(tiet.thoigiankt) if tiet.thoigiankt else None
        } if tiet else None
        
        res.append(d)
    return res

# ---------------------------------------------------------
# API ĐIỂM DANH
# ---------------------------------------------------------
@router.get("/diemdanh")
async def get_diemdanh(tkb_tiet_id: str = None, ngay_diem_danh: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(DiemDanh)
    if tkb_tiet_id and tkb_tiet_id.startswith("in."):
        ids_str = tkb_tiet_id.replace("in.(", "").replace(")", "")
        ids = [int(i) for i in ids_str.split(",") if i.strip()]
        stmt = stmt.where(DiemDanh.tkb_tiet_id.in_(ids))
        
    if ngay_diem_danh and ngay_diem_danh.startswith("eq."):
        date_str = ngay_diem_danh.replace("eq.", "")
        target_date = datetime.date.fromisoformat(date_str)
        stmt = stmt.where(DiemDanh.ngay_diem_danh == target_date)
        
    result = await db.execute(stmt)
    res = []
    for d in result.scalars().all():
        d_dict = model_to_dict(d)
        d_dict["ngay_diem_danh"] = str(d.ngay_diem_danh) if d.ngay_diem_danh else None
        d_dict["created_at"] = str(d.created_at) if d.created_at else None
        res.append(d_dict)
    return res
# ---------------------------------------------------------
# WEBSOCKET: XỬ LÝ ĐIỂM DANH REAL-TIME BẰNG AI
# ---------------------------------------------------------
@router.websocket("/ws/attendance/{tkb_tiet_id}")
async def websocket_attendance(websocket: WebSocket, tkb_tiet_id: int):
    await websocket.accept()
    print(f"[WebSocket] Mở kết nối điểm danh cho Tiết ID: {tkb_tiet_id}")
    
    try:
        while True:
            # 1. Nhận dữ liệu JSON từ App Client gửi lên (chứa base64 của ảnh)
            data = await websocket.receive_json()
            base64_img = data.get("image")
            
            if not base64_img:
                continue

            # 2. Giải mã Base64 thành mảng Numpy (cv2 image)
            img_data = base64.b64decode(base64_img)
            np_arr = np.frombuffer(img_data, np.uint8)
            img_cv2 = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # Chuyển BGR (OpenCV) sang RGB (chuẩn của PyTorch/AI)
            img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)

            # 3. AI BƯỚC 1: Chống giả mạo (Anti-Spoofing)
            is_real = face_engine.detect_spoof(img_rgb)
            if not is_real:
                await websocket.send_json({
                    "status": "spoof", 
                    "message": "Phát hiện giả mạo khuôn mặt!"
                })
                continue

            # 4. AI BƯỚC 2: Trích xuất Vector
            embedding = face_engine.extract_embedding(img_rgb)
            
            # TODO: Lát nữa chúng ta sẽ viết câu lệnh so sánh pgvector ở đây!
            # Tạm thời trả về kết quả thành công ảo để xem App phản ứng thế nào.
            
            await websocket.send_json({
                "status": "success",
                "message": "Hợp lệ",
                "student_id": "SV_TEST_001",
                "name": "Bé Mèo Nhỏ (Giả lập)",
                "embedding_length": len(embedding)
            })
            
    except WebSocketDisconnect:
        print(f"[WebSocket] Đã đóng kết nối cho Tiết ID: {tkb_tiet_id}")
    except Exception as e:
        print(f"[WebSocket Lỗi Kín] {e}")