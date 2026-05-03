"""
server/app/ai/engine.py
=======================
Lõi AI Nhận diện Khuôn mặt (Face Recognition Core Engine)

Kiến trúc:
    - InsightFace FaceAnalysis (buffalo_s): RetinaFace detector + ArcFace 512-D embedding
    - FIQA (Face Image Quality Assessment): Laplacian Variance để lọc ảnh mờ
    - Anti-Spoof: MiniFASNet liveness detection via ONNX Runtime
    - Calibration: Giải méo quang học cho webcam góc rộng (tuỳ chọn, graceful fallback)
    - Detection Fallback: OpenCV DNN khi InsightFace không khả dụng
    - Singleton Pattern: Khởi tạo 1 lần, dùng toàn application
"""

import cv2
import base64
import numpy as np
import onnxruntime as ort
from typing import List, Tuple
from pathlib import Path
from insightface.app import FaceAnalysis
from app.ai.calibration import CameraCalibrator
from app.core.config import ANTI_SPOOF_MODEL
from app.services.system_config_service import config_service


# ==============================================================================
# HẰNG SỐ CẤU HÌNH
# ==============================================================================

# Tên model InsightFace (buffalo_s: nhẹ nhàng, phù hợp cho triển khai thực tế)
MODEL_NAME = "buffalo_s"

# Kích thước ảnh đầu vào cho bộ dò khuôn mặt (RetinaFace)
# 640x640 là tốt nhất cho phát hiện đa khuôn mặt; giảm xuống 320x320 nếu cần tốc độ hơn
DETECTION_SIZE = (640, 640)


# ==============================================================================
# FAKE FACE HELPER – Dùng khi fallback sang OpenCV DNN detection
# ==============================================================================

class FakeFace:
    """Minimal face object compatible with InsightFace Face interface."""
    def __init__(self, bbox):
        self.bbox = np.array(bbox, dtype=np.float32)
        self.normed_embedding = np.zeros(512, dtype=np.float32)


class FaceEngine:
    """
    Singleton lõi AI. Chịu trách nhiệm:
        1. Phát hiện khuôn mặt (Detection) – InsightFace hoặc OpenCV DNN fallback
        2. Trích xuất vector đặc trưng (Feature Extraction / Embedding)
        3. Đánh giá chất lượng ảnh (FIQA)
        4. Giải méo quang học (Undistortion / Calibration)
        5. Anti-Spoof liveness detection (MiniFASNet via ONNX)
    """

    def __init__(self):
        print("[AI Core] ═══════════════════════════════════════════════════")
        print("[AI Core] Đang khởi động lõi AI InsightFace...")

        # -----------------------------------------------------------------
        # 1. KHỞI TẠO INSIGHTFACE (với OpenCV DNN Fallback)
        # -----------------------------------------------------------------
        providers = ort.get_available_providers()
        ctx_id = 0 if "CUDAExecutionProvider" in providers else -1
        device_label = "GPU (CUDA)" if ctx_id == 0 else "CPU"

        self._opencv_net = None  # Fallback DNN detector

        try:
            self.app = FaceAnalysis(
                name=MODEL_NAME,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            self.app.prepare(ctx_id=ctx_id, det_size=DETECTION_SIZE)
            print(f"[AI Core] InsightFace ({MODEL_NAME}) khởi tạo thành công → Chạy trên: {device_label}")
        except Exception as e:
            print(f"[AI Core] InsightFace init failed, loading OpenCV DNN fallback: {e}")
            prototxt = Path(__file__).parent / "models" / "deploy.prototxt"
            caffemodel = Path(__file__).parent / "models" / "res10_300x300_ssd_iter_140000.caffemodel"
            if prototxt.is_file() and caffemodel.is_file():
                self._opencv_net = cv2.dnn.readNetFromCaffe(str(prototxt), str(caffemodel))
                print("[AI Core] OpenCV DNN fallback detector loaded.")
            else:
                print("[AI Core][WARN] OpenCV DNN model files not found. Detection unavailable.")
            self.app = None 

        # -----------------------------------------------------------------
        # 2. KHỞI TẠO CALIBRATOR
        # -----------------------------------------------------------------
        try:
            self.calibrator = CameraCalibrator()
            self._calibration_enabled = True
            print("[AI Core] Camera Calibrator (Undistortion) đã được kích hoạt.")
        except Exception as e:
            self.calibrator = None
            self._calibration_enabled = False
            print(f"[AI Core][WARN] Không thể khởi tạo Calibrator: {e}. Bỏ qua bước giải méo.")

        # -----------------------------------------------------------------
        # 3. KHỞI TẠO ANTI-SPOOF MODEL
        # -----------------------------------------------------------------
        anti_spoof_path = Path(__file__).parent / "models" / ANTI_SPOOF_MODEL
        if anti_spoof_path.is_file():
            try:
                self.anti_spoof_session = ort.InferenceSession(str(anti_spoof_path))
                print(f"[AI Core] Anti-Spoof model ({ANTI_SPOOF_MODEL}) loaded successfully.")
            except Exception as e:
                self.anti_spoof_session = None
                print(f"[AI Core][WARN] Failed to load Anti-Spoof model: {e}")
        else:
            self.anti_spoof_session = None
            print(f"[AI Core] Warning: Anti-spoof model not found at {anti_spoof_path}, skipping check.")

        print("[AI Core] Hệ thống nhận diện khuôn mặt đã sẵn sàng!")
        print("[AI Core] ═══════════════════════════════════════════════════")

    # ==========================================================================
    # PRIVATE HELPERS
    # ==========================================================================

    def _decode_base64_to_bgr(self, b64_image: str) -> np.ndarray | None:
        try:
            if "," in b64_image:
                b64_image = b64_image.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_image)
            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"[AI Engine][_decode_base64_to_bgr] Lỗi giải mã Base64: {e}")
            return None

    def _undistort(self, frame: np.ndarray) -> np.ndarray:
        if self._calibration_enabled and self.calibrator is not None:
            return self.calibrator.undistort_image(frame)
        return frame

    def _get_faces_sorted_by_area(self, frame_bgr: np.ndarray) -> list:
        if self.app is None:
            return []
        faces = self.app.get(frame_bgr)
        if not faces:
            return []
        faces.sort(
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            reverse=True,
        )
        return faces

    def _detect_faces_opencv(self, img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        if self._opencv_net is None:
            return []
        blob = cv2.dnn.blobFromImage(img, 1.0, (300, 300), (104.0, 177.0, 123.0))
        self._opencv_net.setInput(blob)
        detections = self._opencv_net.forward()
        h, w = img.shape[:2]
        bboxes = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.6:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                x1, y1, x2, y2 = box.astype(int)
                bboxes.append((x1, y1, x2, y2))
        return bboxes

    def _is_live_face(self, frame_bgr: np.ndarray, face: any, fiqa_score: float = 1.0) -> bool:
        """
        Kiểm tra tính thật/giả của khuôn mặt dựa trên modelrgb.onnx.
        Bổ sung: Quality-aware thresholding để giảm False Positive trên camera PC chất lượng thấp.
        """
        if self.anti_spoof_session is None:
            return True
        try:
            # 1. Cắt vùng khuôn mặt với margin 1.5
            kps = face.kps
            x_list, y_list = kps[:, 0], kps[:, 1]
            x, y = round(float(min(x_list))), round(float(min(y_list)))
            w, h = round(float(max(x_list))) - x, round(float(max(y_list))) - y
            side = max(w, h)
            margin = 1.5
            x_m, y_m = int(side * margin / 2), int(side * margin / 2)
            nx1, nx2 = max(0, x - x_m), min(frame_bgr.shape[1], x + side + x_m)
            ny1, ny2 = max(0, y - y_m), min(frame_bgr.shape[0], y + side + y_m)
            
            face_crop = frame_bgr[ny1:ny2, nx1:nx2]
            if face_crop.size == 0: return True

            # 2. Preprocessing [-1, 1]
            img_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img_rgb, (112, 112))
            blob = (img.astype(np.float32) / 127.5) - 1.0
            blob = np.transpose(blob, (2, 0, 1))[np.newaxis, ...]
            
            # 3. Inference
            out = self.anti_spoof_session.run(None, {self.anti_spoof_session.get_inputs()[0].name: blob})[0]
            spoof_prob = float(out[0][0])
            
            # 4. Ngưỡng động dựa trên chất lượng ảnh (FIQA)
            # Nếu ảnh mờ (thường là PC), ta nới lỏng ngưỡng thêm 0.05 để tránh báo nhầm
            base_threshold = config_service.get_anti_spoof_threshold()
            dynamic_threshold = base_threshold
            if fiqa_score < 0.25:
                dynamic_threshold += 0.05
                
            is_live = spoof_prob <= dynamic_threshold
            
            status_str = "\033[92mLIVE\033[0m" if is_live else "\033[91mSPOOF\033[0m"
            print(f"[Anti-Spoof] Score: {spoof_prob:.4f} | Threshold: {dynamic_threshold:.4f} (FIQA: {fiqa_score:.2f}) | Status: {status_str}")
            
            return is_live
        except Exception as e:
            print(f"[AI Engine] Anti-spoof error: {e}")
            return True

    # ==========================================================================
    # PUBLIC API
    # ==========================================================================

    def evaluate_fiqa(self, face_crop_bgr: np.ndarray) -> float:
        if face_crop_bgr is None or face_crop_bgr.size == 0:
            return 0.0
        gray = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        score = laplacian_var / 200.0
        return float(min(score, 1.0))

    def extract_embedding(self, img_rgb: np.ndarray) -> list | None:
        try:
            frame_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            faces = self._get_faces_sorted_by_area(frame_bgr)
            if not faces:
                return None
            return faces[0].normed_embedding.tolist()
        except Exception as e:
            print(f"[AI Engine][extract_embedding] Lỗi: {e}")
            return None

    def extract_fused_embedding(self, base64_images: list[str]) -> list:
        embeddings: list[np.ndarray] = []
        for idx, b64 in enumerate(base64_images):
            try:
                frame = self._decode_base64_to_bgr(b64)
                if frame is None: continue
                frame = self._undistort(frame)
                faces = self._get_faces_sorted_by_area(frame)
                if not faces: continue
                embeddings.append(faces[0].normed_embedding)
            except Exception: continue

        if not embeddings:
            raise ValueError("Không thể trích xuất được khuôn mặt hợp lệ!")

        arr = np.array(embeddings, dtype=np.float32)
        mean_vec = np.mean(arr, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm == 0: raise ValueError("Vector trung bình lỗi.")
        return (mean_vec / norm).tolist()

    def process_attendance_frame(self, b64_image: str, mode: str = "1") -> dict:
        try:
            spoof_detected = False
            frame = self._decode_base64_to_bgr(b64_image)
            if frame is None: return {"embeddings": [], "spoof_detected": False}
            frame = self._undistort(frame)
            ih, iw = frame.shape[:2]

            if self.app:
                faces = self.app.get(frame)
            else:
                bboxes = self._detect_faces_opencv(frame)
                faces = [FakeFace(bbox=b) for b in bboxes]

            if not faces: return {"embeddings": [], "spoof_detected": False}

            face_results: list[dict] = []
            for face in faces:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = max(0, bbox[0]), max(0, bbox[1]), min(iw, bbox[2]), min(ih, bbox[3])
                area = (x2 - x1) * (y2 - y1)
                if area < config_service.get_min_face_area(): continue

                face_crop = frame[y1:y2, x1:x2]
                fiqa_score = self.evaluate_fiqa(face_crop)
                if fiqa_score < config_service.get_fiqa_threshold(): continue

                # BƯỚC 7: Anti-Spoof – Kiểm tra liveness
                # Dùng frame gốc, face object và điểm chất lượng (để dùng ngưỡng động)
                if not self._is_live_face(frame, face, fiqa_score):
                    spoof_detected = True
                    continue

                face_results.append({
                    "embedding": face.normed_embedding.tolist(),
                    "area": area,
                })

            if not face_results: 
                return {"embeddings": [], "spoof_detected": spoof_detected}
            
            # Sắp xếp theo diện tích giảm dần để kết quả nhất quán
            face_results.sort(key=lambda x: x["area"], reverse=True)

            return {
                "embeddings": [f["embedding"] for f in face_results], 
                "spoof_detected": spoof_detected
            }
        except Exception as e:
            print(f"[AI Engine] Error: {e}")
            return {"embeddings": [], "spoof_detected": False}


# SINGLETON INSTANCE
face_engine = FaceEngine()