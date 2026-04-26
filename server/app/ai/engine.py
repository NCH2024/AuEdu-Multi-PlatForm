import cv2
import numpy as np
import base64
import insightface
from insightface.app import FaceAnalysis
import onnxruntime as ort
from app.ai.calibration import CameraCalibrator

class FaceEngine:
    def __init__(self):
        print("[AI Core] Đang khởi động lõi AI bằng InsightFace...")
        
        # 1. Khởi tạo InsightFace với model buffalo_s (RetinaFace dò tìm + MobileFaceNet/ArcFace 512D)
        # Model 'buffalo_s' rất nhẹ và chính xác, phù hợp cho triển khai thực tế đa môi trường.
        self.app = FaceAnalysis(name='buffalo_s', root='~/.insightface/models')
        
        # Tự động nhận diện thiết bị (GPU/CPU)
        providers = ort.get_available_providers()
        ctx_id = 0 if 'CUDAExecutionProvider' in providers else -1
        
        # Cấu hình ctx_id (0: GPU đầu tiên, -1: CPU) và kích thước dò tìm
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        device_name = "GPU" if ctx_id == 0 else "CPU"
        print(f"[AI Core] Đã cấu hình InsightFace chạy trên: {device_name}")
        
        # 2. Khởi tạo bộ Calibration chống méo ảnh góc rộng
        self.calibrator = CameraCalibrator()
        
        print("[AI Core] Hệ thống nhận diện chuẩn công nghiệp đã sẵn sàng!")

    def evaluate_fiqa(self, face_crop: np.ndarray) -> float:
        """
        Đánh giá chất lượng khuôn mặt (Face Image Quality Assessment - FIQA).
        Thuật toán: Tính phương sai của ma trận đạo hàm bậc 2 (Laplacian) để đo độ sắc nét.
        Trả về: Điểm từ 0.0 đến 1.0.
        """
        if face_crop is None or face_crop.size == 0:
            return 0.0
            
        # Chuyển đổi sang ảnh xám
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        
        # Tính toán Laplacian Variance (độ sắc nét)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Giả định ngưỡng 200.0 là sắc nét đối với webcam thông thường.
        score = laplacian_var / 200.0
        
        # Giới hạn trần ở 1.0
        return float(min(score, 1.0))

    def extract_fused_embedding(self, base64_images: list) -> list:
        """
        Mean Aggregation (Pha Đào tạo - Enrollment):
        Nhận vào 1 danh sách 10-15 ảnh Base64 của cùng 1 người.
        Giải méo, dò mặt, trích xuất vector 512D, sau đó tính trung bình (np.mean)
        và L2-Normalization để tạo ra 1 siêu vector (Anchor) duy nhất đại diện cho người đó.
        """
        embeddings = []
        
        for b64 in base64_images:
            try:
                # 1. Giải mã Base64
                img_data = base64.b64decode(b64.split(",")[1] if "," in b64 else b64)
                np_arr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                
                # 2. Giải méo quang học
                frame = self.calibrator.undistort_image(frame)
                
                # 3. Dò tìm khuôn mặt (Trả về BGR, InsightFace yêu cầu BGR theo mặc định cv2)
                faces = self.app.get(frame)
                
                if len(faces) == 0:
                    continue
                    
                # 4. Lấy khuôn mặt to nhất (nhân vật chính)
                # bounding box format: [x1, y1, x2, y2]
                faces.sort(key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
                target_face = faces[0]
                
                # Trích xuất vector 512D (đã tự động được l2 normalize trong insightface)
                emb = target_face.normed_embedding
                embeddings.append(emb)
                
            except Exception as e:
                print(f"[AI Extract Lỗi] {e}")
                continue 
                
        if not embeddings:
            raise ValueError("Không thể trích xuất được khuôn mặt hợp lệ từ các ảnh được gửi!")

        # 5. MEAN AGGREGATION & L2-NORMALIZATION
        arr_embeddings = np.array(embeddings, dtype=np.float32)
        mean_vector = np.mean(arr_embeddings, axis=0)
        final_vector = mean_vector / np.linalg.norm(mean_vector)
        
        return final_vector.tolist()
    
    def process_attendance_frame(self, b64_image: str, mode: str = "1"):
        """
        Pha Điểm danh (Inference): Xử lý frame thời gian thực gửi từ WebSockets.
        Tích hợp Calibration, InsightFace Detection + ArcFace, và FIQA.
        """
        try:
            # 1. Giải mã ảnh
            img_data = base64.b64decode(b64_image.split(",")[1] if "," in b64_image else b64_image)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None: 
                return []
            
            # 2. Tiền xử lý: Kéo phẳng ảnh (Undistort) để tránh sai lệch ở góc rộng
            frame = self.calibrator.undistort_image(frame)
            ih, iw = frame.shape[:2]

            # 3. Dò tìm toàn bộ khuôn mặt trong khung hình
            faces = self.app.get(frame)
            
            face_list = []
            for face in faces:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                
                # Giới hạn tọa độ hợp lệ
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(iw, x2), min(ih, y2)
                
                # Kiểm tra diện tích
                area = (x2 - x1) * (y2 - y1)
                if area <= 0: continue
                
                # 4. FIQA - Cắt ảnh khuôn mặt để đo độ nét
                face_crop = frame[y1:y2, x1:x2]
                fiqa_score = self.evaluate_fiqa(face_crop)
                
                # 5. Bộ lọc FIQA: Bỏ qua các ảnh quá mờ nhòe (ngưỡng 0.05 tương đương độ nét cơ bản của Webcam)
                if fiqa_score >= 0.05:
                    face_list.append({
                        "embedding": face.normed_embedding.tolist(),
                        "area": area,
                        "fiqa": fiqa_score
                    })

            if not face_list: 
                return []
            
            # 6. Trả về theo cấu hình Mode (1 người hay Toàn lớp)
            if mode == "1":
                # Lấy mặt to nhất (gần camera nhất)
                face_list.sort(key=lambda x: x["area"], reverse=True)
                return [face_list[0]["embedding"]]
            else:
                # Lấy tất cả
                return [f["embedding"] for f in face_list]

        except Exception as e:
            print(f"[AI Engine Attendance Error] {e}")
            return []

# Khởi tạo thể hiện Singleton để sử dụng toàn cục
face_engine = FaceEngine()