"""
server/app/services/attendance_cache.py
=======================================
In-memory Cache cho luồng điểm danh (High-Performance Attendance Pipeline).
Giảm tải "N+1 queries" bằng cách lưu trữ FaceEmbedding và thông tin SinhVien
vào RAM khi WebSocket mở kết nối.
"""

import asyncio
import numpy as np
from typing import Optional, Dict, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import SinhVien, FaceEmbedding, ThoiKhoaBieu, TKBTiet

class ClassCacheData:
    def __init__(self):
        self.students: Dict[int, dict] = {}
        self.embeddings: List[FaceEmbedding] = []
        self.vectors: np.ndarray = np.array([])
        self.vector_sv_ids: List[int] = []

class AttendanceCache:
    def __init__(self):
        self._cache: Dict[int, ClassCacheData] = {}
        self._lock = asyncio.Lock()

    async def load_class_data(self, tkb_tiet_id: int, db: AsyncSession):
        """
        Tải toàn bộ vector khuôn mặt và thông tin sinh viên của tiết học vào bộ nhớ.
        """
        async with self._lock:
            if tkb_tiet_id in self._cache:
                return # Đã được tải trước đó
            
            print(f"[AttendanceCache] Đang tải dữ liệu cho tkb_tiet_id={tkb_tiet_id}...")
            
            # 1. Tìm lop_id
            stmt_lop = select(ThoiKhoaBieu.lop_id).join(TKBTiet, TKBTiet.tkb_id == ThoiKhoaBieu.id).where(TKBTiet.id == tkb_tiet_id)
            lop_id = await db.scalar(stmt_lop)
            
            if not lop_id:
                print(f"[AttendanceCache] Không tìm thấy lop_id cho tkb_tiet_id={tkb_tiet_id}")
                return
                
            # 2. Lấy danh sách SinhVien
            stmt_sv = select(SinhVien).where(SinhVien.class_id == lop_id)
            students = (await db.scalars(stmt_sv)).all()
            sv_ids = [s.id for s in students]
            
            if not sv_ids:
                print(f"[AttendanceCache] Không có sinh viên nào trong lớp {lop_id}")
                return
                
            # 3. Lấy FaceEmbedding
            stmt_emb = select(FaceEmbedding).where(FaceEmbedding.sv_id.in_(sv_ids))
            embeddings = (await db.scalars(stmt_emb)).all()
            
            # 4. Lưu vào cache
            cache_data = ClassCacheData()
            cache_data.students = {
                s.id: {"id": s.id, "hodem": s.hodem, "ten": s.ten} 
                for s in students
            }
            cache_data.embeddings = list(embeddings)
            
            # Chuyển vector sang Numpy Array để tính toán siêu tốc
            vectors_list = []
            vector_sv_ids = []
            for emb in embeddings:
                # pgvector trả về numpy array hoặc list
                vec = np.array(emb.embedding, dtype=np.float32)
                vectors_list.append(vec)
                vector_sv_ids.append(emb.sv_id)
                
            if vectors_list:
                cache_data.vectors = np.vstack(vectors_list)
                cache_data.vector_sv_ids = vector_sv_ids
                
            self._cache[tkb_tiet_id] = cache_data
            print(f"[AttendanceCache] Tải thành công {len(students)} SV, {len(embeddings)} vectors cho tkb_tiet_id={tkb_tiet_id}")

    async def clear_class_data(self, tkb_tiet_id: int):
        """Xoá cache khi kết thúc phiên điểm danh."""
        async with self._lock:
            if tkb_tiet_id in self._cache:
                del self._cache[tkb_tiet_id]
                print(f"[AttendanceCache] Đã xoá cache cho tkb_tiet_id={tkb_tiet_id}")

    def find_best_match(self, tkb_tiet_id: int, target_embedding: list, threshold: float = 0.45) -> Tuple[Optional[dict], Optional[float]]:
        """
        Tìm sinh viên khớp nhất dựa trên khoảng cách Cosine dùng Numpy.
        Độ trễ dự kiến: < 1ms
        Trường hợp cache chưa tải, trả về (None, -1.0).
        """
        if tkb_tiet_id not in self._cache:
            return None, -1.0
            
        cache_data = self._cache[tkb_tiet_id]
        if cache_data.vectors.size == 0:
            return None, -1.0
            
        target_vec = np.array(target_embedding, dtype=np.float32)
        
        # Khoảng cách Cosine = 1 - Cosine Similarity
        # InsightFace embeddings thường đã được L2-normalized
        # distance = 1 - dot_product
        dot_products = np.dot(cache_data.vectors, target_vec)
        distances = 1.0 - dot_products
        
        best_idx = np.argmin(distances)
        best_distance = distances[best_idx]
        
        if best_distance >= threshold:
            # Ngưỡng an toàn
            return None, best_distance
            
        best_sv_id = cache_data.vector_sv_ids[best_idx]
        best_student = cache_data.students.get(best_sv_id)
        
        return best_student, best_distance

# Singleton instance
attendance_cache = AttendanceCache()
