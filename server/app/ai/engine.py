# Server_Core/app/ai/engine.py
import cv2
import numpy as np
import torch
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

face_engine = FaceEngine()