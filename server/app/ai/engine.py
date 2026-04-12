# Server_Core/app/ai/engine.py
import cv2
import numpy as np
import torch
import base64
import os
from torchvision import transforms
import torch.nn.functional as F

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

class FaceEngine:
    def __init__(self):
        # 1. Khởi tạo thiết bị tính toán (Ưu tiên GPU nếu có)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[AI Core] Đang khởi động lõi AI trên thiết bị: {self.device.type.upper()}")
        
        # 2. Định nghĩa các bộ tiền xử lý ảnh (Pipelines)
        # MobileFaceNet yêu cầu ảnh 112x112, chuẩn hóa (mean=0.5, std=0.5)
        self.face_transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
        
        # Mini-FASNet V2 thường dùng ảnh 80x80
        self.fas_transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((80, 80)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        # 3. Load Trọng số Mô hình (Tạm thời dùng dummy_model nếu thiếu file cấu trúc class)
        self.fas_model = self._load_model("MiniFASNetV2.pth", is_fas=True)
        self.face_model = self._load_model("mobilefacenet_model_best.pth", is_fas=False)
        
        print("[AI Core] Hệ thống nhận diện đã sẵn sàng!")

    def _load_model(self, filename, is_fas):
        """Hàm hỗ trợ load model an toàn"""
        path = os.path.join(MODEL_DIR, filename)
        if not os.path.exists(path):
            print(f"[Cảnh báo] Không tìm thấy {filename}. Sẽ chạy ở chế độ giả lập (Dummy Mode).")
            return None
            
        try:
            # Lưu ý: Lệnh torch.load đối với file .pth dạng state_dict cần có class mạng nơ-ron
            checkpoint = torch.load(path, map_location=self.device)
            print(f"[AI Core] Tải thành công {filename}")
            return checkpoint
        except Exception as e:
            print(f"[Lỗi load model {filename}]: {e}")
            return None

    def detect_spoof(self, image_rgb: np.ndarray) -> bool:
        """Kiểm tra ảnh giả mạo (Anti-Spoofing)"""
        if self.fas_model is None:
            return True # Giả lập: Luôn là người thật nếu chưa có model
            
        try:
            # Tiền xử lý
            tensor_img = self.fas_transform(image_rgb).unsqueeze(0).to(self.device)
            
            # Đưa qua model (Khi có file class MiniFASNet, ta sẽ gọi self.fas_model(tensor_img))
            # Hiện tại trả về True để test thông mạch
            return True 
        except Exception as e:
            print(f"[Lỗi FAS] {e}")
            return False

    def extract_embedding(self, image_rgb: np.ndarray) -> list:
        """Trích xuất vector 512 chiều từ khuôn mặt"""
        try:
            if self.face_model is not None:
                # Tiền xử lý
                tensor_img = self.face_transform(image_rgb).unsqueeze(0).to(self.device)
                
                # Inference qua mạng MobileFaceNet (Cần ráp class MobileFaceNet sau)
                # with torch.no_grad():
                #     features = self.face_model(tensor_img)
                #     features = F.normalize(features, p=2, dim=1)
                #     return features.cpu().numpy().flatten().tolist()
            
            # --- CHẾ ĐỘ TEST KHI CHƯA RÁP CLASS ---
            # Trả về một vector giả 512 chiều được chuẩn hóa (L2-Norm)
            dummy_vec = np.random.rand(512).astype(np.float32)
            dummy_vec = dummy_vec / np.linalg.norm(dummy_vec)
            return dummy_vec.tolist()
            
        except Exception as e:
            print(f"[Lỗi FaceNet] {e}")
            return np.zeros(512, dtype=np.float32).tolist()
        
    def extract_fused_embedding(self, base64_images: list) -> list:
        """Nhận vào mảng Base64, chống giả mạo, và hợp nhất Vector bằng Average Pooling"""
        embeddings = []
        
        for b64 in base64_images:
            try:
                # 1. Giải mã Base64 sang ảnh OpenCV
                img_data = base64.b64decode(b64.split(",")[1] if "," in b64 else b64)
                np_arr = np.frombuffer(img_data, np.uint8)
                img_cv2 = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
                
                # 2. Kiểm tra giả mạo cho TỪNG ẢNH
                if not self.detect_spoof(img_rgb):
                    raise ValueError("Phát hiện giả mạo khuôn mặt trong ảnh lấy mẫu!")
                    
                # 3. Trích xuất Vector
                emb = self.extract_embedding(img_rgb)
                embeddings.append(emb)
            except Exception as e:
                print(f"[AI Lỗi Xử Lý Ảnh] {e}")
                continue # Nếu lỗi 1 ảnh, bỏ qua ảnh đó chụp các ảnh khác
                
        if not embeddings:
            raise ValueError("Không thể trích xuất được khuôn mặt hợp lệ từ các ảnh được gửi!")

        # 4. TÍNH TOÁN AVERAGE POOLING VÀ L2 NORMALIZE
        # Chuyển list python sang numpy array: kích thước (N, 512)
        arr_embeddings = np.array(embeddings, dtype=np.float32)
        
        # Lấy trung bình theo trục dọc (axis=0) để ra 1 vector duy nhất 512 chiều
        mean_vector = np.mean(arr_embeddings, axis=0)
        
        # Chuẩn hóa L2-Normalization (Vector đưa về độ dài = 1)
        final_vector = mean_vector / np.linalg.norm(mean_vector)
        
        return final_vector.tolist()
    
    def process_attendance_frame(self, b64_image: str, mode: str = "1"):
        """
        Xử lý frame điểm danh:
        - mode="1": Chỉ lấy người gần nhất (diện tích mặt lớn nhất)
        - mode="all": Lấy tất cả khuôn mặt phát hiện được
        """
        try:
            # 1. Giải mã ảnh
            img_data = base64.b64decode(b64_image.split(",")[1] if "," in b64_image else b64_image)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None: return []
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ih, iw, _ = frame.shape

            # 2. SỬ DỤNG 'with' ĐỂ TỰ ĐỘNG DỌN DẸP BỘ NHỚ (CHỐNG TRÀN RAM XNNPACK)
            import mediapipe as mp
            with mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
                results = face_detection.process(rgb_frame)

                face_list = []
                if results.detections:
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        x, y, w, h = int(bbox.xmin * iw), int(bbox.ymin * ih), int(bbox.width * iw), int(bbox.height * ih)
                        
                        # Đảm bảo tọa độ hợp lệ
                        x, y = max(0, x), max(0, y)
                        w, h = min(iw - x, w), min(ih - y, h)
                        area = w * h
                        
                        # Cắt khuôn mặt (có padding) để lấy embedding
                        pad = int(w * 0.15)
                        face_crop = frame[max(0, y-pad):min(ih, y+h+pad), max(0, x-pad):min(iw, x+w+pad)]
                        
                        if face_crop.size > 0:
                            embedding = self.extract_embedding(cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB))
                            face_list.append({"embedding": embedding, "area": area})

            # 3. Áp dụng Logic Mode
            if not face_list: return []
            
            if mode == "1":
                # Sắp xếp theo diện tích giảm dần, lấy mặt to nhất (gần nhất)
                face_list.sort(key=lambda x: x["area"], reverse=True)
                return [face_list[0]["embedding"]]
            else:
                # Trả về toàn bộ danh sách vector
                return [f["embedding"] for f in face_list]

        except Exception as e:
            print(f"[AI Engine Attendance Error] {e}")
            return []

face_engine = FaceEngine()