# Server_Core/app/db/models.py
from sqlalchemy import Column, Integer, BigInteger, String, Text, Date, DateTime, Time, ForeignKey, text, Identity, Float, UniqueConstraint, Index, CheckConstraint, JSON, Boolean, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base

class Khoa(Base):
    __tablename__ = 'khoa'
    id = Column(String, primary_key=True)
    tenkhoa = Column(Text)
    email = Column(String, nullable=True) # Thêm email cho Khoa
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class LoaiHocPhan(Base):
    __tablename__ = 'loaihocphan'
    id = Column(Integer, primary_key=True)
    tenloai = Column(Text)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class HocKy(Base):
    __tablename__ = 'hocky'
    id = Column(Integer, Identity(always=True), primary_key=True)
    tenhocky = Column(Text) # term
    namhoc = Column(Text) # year
    so_tuan_hoc = Column(Integer, default=15) # Số tuần học
    loai_hocky = Column(Text, server_default='Chính') # Chính, Hè, Phụ
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class Tiet(Base):
    __tablename__ = 'tiet'
    id = Column(Integer, primary_key=True)
    thoigianbd = Column(Time)
    thoigiankt = Column(Time)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class GiangVien(Base):
    __tablename__ = 'giangvien'
    id = Column(Integer, primary_key=True)
    hodem = Column(Text)
    ten = Column(Text)
    gioitinh = Column(Text)
    diachi = Column(Text)
    sodienthoai = Column(Text)
    khoa_id = Column(String, ForeignKey('khoa.id'))
    auth_id = Column(String)  
    vai_tro = Column(Text, server_default='giangvien')
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    last_login = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

    __table_args__ = (
        CheckConstraint(vai_tro.in_(['giangvien', 'admin', 'super_admin']), name='chk_vai_tro'),
    )

class Lop(Base):
    __tablename__ = 'lop'
    id = Column(String, primary_key=True)
    code = Column(String, nullable=True) # Mã lớp
    tenlop = Column(Text) # Tên lớp
    khoa_id = Column(String, ForeignKey('khoa.id')) # department_id
    semester_id = Column(Integer, ForeignKey('hocky.id'), nullable=True)
    nambd = Column(Integer)
    namkt = Column(Integer)
    khoahoc = Column(Integer)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class SinhVien(Base):
    __tablename__ = 'sinhvien'
    id = Column(Integer, primary_key=True) # ID chính là MSSV
    ma_ho_so = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hodem = Column(Text)
    ten = Column(Text)
    gioitinh = Column(Text)
    ngaysinh = Column(Date)
    noi_sinh = Column(Text)
    dan_toc = Column(String)
    ton_giao = Column(String)
    nguyen_quan = Column(Text)
    ho_khau = Column(Text)
    ngay_vao_doan = Column(Date)
    class_id = Column(String, ForeignKey('lop.id'))
    bac_dao_tao = Column(String)
    ho_ten_cha = Column(String)
    nghe_nghiep_cha = Column(String)
    ho_ten_me = Column(String)
    nghe_nghiep_me = Column(String)
    dien_thoai = Column(String)
    trang_thai = Column(String, default="Đang học")
    ngay_ra_quyet_dinh = Column(Date)
    diachi = Column(Text)
    ghichu = Column(Text)
    anhdaidien = Column(Text)
    face_vector = Column(Vector(512), nullable=True) 
    
    # --- AUDIT TRAIL & SOFT DELETE ---
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class HocPhan(Base):
    __tablename__ = 'hocphan'
    id = Column(Integer, primary_key=True)
    tenhocphan = Column(Text)
    sotinchi = Column(Integer)
    loaihp_id = Column(Integer, ForeignKey('loaihocphan.id'))
    sobuoi = Column(Integer)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class ThoiKhoaBieu(Base):
    __tablename__ = 'thoikhoabieu'
    id = Column(Integer, Identity(always=True), primary_key=True)
    hocphan_id = Column(Integer, ForeignKey('hocphan.id'))
    hocky_id = Column(Integer, ForeignKey('hocky.id'))
    lop_id = Column(String, ForeignKey('lop.id'))
    giangvien_id = Column(Integer, ForeignKey('giangvien.id'))
    tuan_hoc_id = Column(Integer, ForeignKey('tuan_hoc.id'), nullable=True) # None = Tất cả các tuần
    
    # AI Config Parameters (Chuyển từ bảng cũ sang đây)
    ai_threshold = Column(Float, default=0.6)
    anti_spoofing = Column(Boolean, default=True)
    fiqa_threshold = Column(Float, default=0.5)
    
    # --- AUDIT TRAIL & SOFT DELETE ---
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class TKBTiet(Base):
    __tablename__ = 'tkb_tiet'
    id = Column(Integer, Identity(always=True), primary_key=True)
    tkb_id = Column(Integer, ForeignKey('thoikhoabieu.id'))
    tiet_id = Column(Integer, ForeignKey('tiet.id'))
    thu = Column(Integer)
    phong_hoc = Column(Text)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class DiemDanh(Base):
    __tablename__ = 'diemdanh'
    id = Column(Integer, Identity(always=True), primary_key=True)
    sv_id = Column(Integer, ForeignKey('sinhvien.id'))
    tkb_tiet_id = Column(Integer, ForeignKey('tkb_tiet.id'))
    
    # --- THÊM CÁC TRƯỜNG MỚI ---
    vitri = Column(Text, nullable=True) # Tọa độ hoặc tên phòng
    device_id = Column(Text, nullable=True)
    client_version = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True) # Điểm AI nhận diện
    note = Column(Text, nullable=True) # Ghi chú thêm (đi trễ, v.v.)
    
    ngay_diem_danh = Column(Date)
    trang_thai = Column(Text, default="Có mặt") # Có mặt / Vắng / Đi trễ
    
    # --- AUDIT TRAIL & SOFT DELETE ---
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

    # --- RÀNG BUỘC & CHỈ MỤC (INDEX) ---
    __table_args__ = (
        # Đảm bảo 1 sinh viên không bị điểm danh 2 lần trong cùng 1 tiết + 1 ngày
        UniqueConstraint('sv_id', 'tkb_tiet_id', 'ngay_diem_danh', name='uq_diemdanh_sv_tiet_ngay'),
        # Index tối ưu hóa cho các query báo cáo
        Index('idx_diemdanh_ngay', 'ngay_diem_danh'),
        Index('idx_diemdanh_tkb', 'tkb_tiet_id'),
    )

class FaceEmbedding(Base):
    __tablename__ = 'face_embeddings'
    sv_id = Column(Integer, ForeignKey('sinhvien.id'), primary_key=True)
    embedding = Column(Vector(512), nullable=False) 
    
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    trained_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    model_version = Column(Text, nullable=True, default="insightface_buffalo_s")  # Model version dùng để trích xuất embedding

class ThongBao(Base):
    __tablename__ = 'thongbao'
    id = Column(BigInteger, Identity(always=True), primary_key=True)
    tieu_de = Column(Text)
    noi_dung = Column(Text)
    giangvien_id = Column(Integer, ForeignKey('giangvien.id'))
    hinh_anh = Column(Text)
    link_web = Column(Text)
    
    # --- AUDIT TRAIL & SOFT DELETE ---
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class TuanHoc(Base):
    __tablename__ = 'tuan_hoc'
    id = Column(Integer, Identity(always=True), primary_key=True)
    hocky_id = Column(Integer, ForeignKey('hocky.id'))
    ten_tuan = Column(Text)
    ngay_bat_dau = Column(Date)
    ngay_ket_thuc = Column(Date)

    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class SystemConfig(Base):
    __tablename__ = 'system_config'
    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(BigInteger, Identity(always=True), primary_key=True)
    user_id = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    action = Column(String, nullable=False) # VD: CREATE, UPDATE, DELETE, LOGIN
    entity = Column(String, nullable=True) # VD: SinhVien, DiemDanh, SystemConfig
    entity_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True) # Chi tiết nội dung thay đổi
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=text('now()'))

    __table_args__ = (
        Index('idx_audit_action', 'action'),
        Index('idx_audit_created_at', 'created_at'),
        Index('idx_audit_user', 'user_id'),
    )

# Hướng dẫn tạo Migration:
# 1. alembic revision --autogenerate -m "Add admin tables and columns"
# 2. alembic upgrade head

# Bảng AttendanceSchedule cũ đã bị xóa để gom vào ThoiKhoaBieu
