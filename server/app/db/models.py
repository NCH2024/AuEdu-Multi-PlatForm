# Server_Core/app/db/models.py
from sqlalchemy import Column, Integer, BigInteger, String, Text, Date, DateTime, Time, ForeignKey, text, Identity
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base

class Khoa(Base):
    __tablename__ = 'khoa'
    id = Column(String, primary_key=True)
    tenkhoa = Column(Text)
    created_at = Column(DateTime, server_default=text('now()'))

class LoaiHocPhan(Base):
    __tablename__ = 'loaihocphan'
    id = Column(Integer, primary_key=True)
    tenloai = Column(Text)
    created_at = Column(DateTime, server_default=text('now()'))

class HocKy(Base):
    __tablename__ = 'hocky'
    id = Column(Integer, primary_key=True)
    tenhocky = Column(Text)
    namhoc = Column(Text)
    created_at = Column(DateTime, server_default=text('now()'))

class Tiet(Base):
    __tablename__ = 'tiet'
    id = Column(Integer, primary_key=True)
    thoigianbd = Column(Time)
    thoigiankt = Column(Time)
    created_at = Column(DateTime, server_default=text('now()'))

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
    vai_tro = Column(Text)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))

class Lop(Base):
    __tablename__ = 'lop'
    id = Column(String, primary_key=True)
    tenlop = Column(Text)
    khoa_id = Column(String, ForeignKey('khoa.id'))
    nambd = Column(Integer)
    namkt = Column(Integer)
    khoahoc = Column(Integer)
    created_at = Column(DateTime, server_default=text('now()'))

class SinhVien(Base):
    __tablename__ = 'sinhvien'
    id = Column(Integer, primary_key=True)
    hodem = Column(Text)
    ten = Column(Text)
    gioitinh = Column(Text)
    diachi = Column(Text)
    ngaysinh = Column(Date)
    class_id = Column(String, ForeignKey('lop.id'))
    ghichu = Column(Text)
    anhdaidien = Column(Text)
    sinhtrachoc = Column(Text) 
    
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

class ThoiKhoaBieu(Base):
    __tablename__ = 'thoikhoabieu'
    id = Column(Integer, Identity(always=True), primary_key=True)
    hocphan_id = Column(Integer, ForeignKey('hocphan.id'))
    hocky_id = Column(Integer, ForeignKey('hocky.id'))
    lop_id = Column(String, ForeignKey('lop.id'))
    giangvien_id = Column(Integer, ForeignKey('giangvien.id'))
    
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

class DiemDanh(Base):
    __tablename__ = 'diemdanh'
    id = Column(Integer, Identity(always=True), primary_key=True)
    sv_id = Column(Integer, ForeignKey('sinhvien.id'))
    tkb_tiet_id = Column(Integer, ForeignKey('tkb_tiet.id'))
    vitri = Column(Text)
    ngay_diem_danh = Column(Date)
    trang_thai = Column(Text)
    
    # --- AUDIT TRAIL & SOFT DELETE ---
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)
    deleted_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True)

class FaceEmbedding(Base):
    __tablename__ = 'face_embeddings'
    sv_id = Column(Integer, ForeignKey('sinhvien.id'), primary_key=True)
    embedding = Column(Vector(512), nullable=False) 
    
    # --- AUDIT TRAIL --- (Bảng này thường không soft delete, đào tạo lại thì update ghi đè lên)
    created_at = Column(DateTime, server_default=text('now()'))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    trained_by = Column(Integer, ForeignKey('giangvien.id'), nullable=True) # Lưu vết ai đã chụp ảnh đào tạo

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