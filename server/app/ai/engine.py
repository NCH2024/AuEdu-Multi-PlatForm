"""
server/app/ai/engine.py
=======================
Lõi AI Nhận diện Khuôn mặt (Face Recognition Core Engine)

Kiến trúc:
    - InsightFace FaceAnalysis (buffalo_s): RetinaFace detector + MobileFaceNet/ArcFace 512-D embedding
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
from app.core.config import FIQA_THRESHOLD, ANTI_SPOOF_MODEL


# ==============================================================================
# HẰNG SỐ CẤU HÌNH
# ==============================================================================

# Tên model InsightFace (buffalo_s: nhẹ nhàng, phù hợp cho triển khai thực tế)
MODEL_NAME = "buffalo_s"

# Kích thước ảnh đầu vào cho bộ dò khuôn mặt (RetinaFace)
# 640x640 là tốt nhất cho phát hiện đa khuôn mặt; giảm xuống 320x320 nếu cần tốc độ hơn
DETECTION_SIZE = (640, 640)

# Ngưỡng diện tích khuôn mặt tối thiểu (pixel^2) để bỏ qua các khuôn mặt quá nhỏ
MIN_FACE_AREA = 900  # 30x30 pixels


# ==============================================================================
# FAKFACE HELPER – Dùng khi fallback sang OpenCV DNN detection
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
        #    - providers=[CUDA, CPU]: Tự động dùng GPU nếu có, fallback CPU
        #    - name='buffalo_s': Model nhẹ - RetinaFace + MobileFaceNet 512-D
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
            # ctx_id=0 → GPU đầu tiên, ctx_id=-1 → CPU mode
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
            self.app = None  # disable InsightFace path

        # -----------------------------------------------------------------
        # 2. KHỞI TẠO CALIBRATOR (Graceful Fallback)
        #    Nếu tham số calibration chưa sẵn sàng (lỗi bất ngờ), hệ thống
        #    vẫn tiếp tục chạy mà không crash, chỉ bỏ bước giải méo.
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
        # 3. KHỞI TẠO ANTI-SPOOF MODEL (MiniFASNet via ONNX)
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
        """
        Giải mã chuỗi Base64 (có thể có tiền tố 'data:image/...;base64,') thành
        ảnh NumPy BGR (định dạng OpenCV).

        Trả về None nếu dữ liệu không hợp lệ hoặc giải mã thất bại.
        """
        try:
            # Tách bỏ tiền tố Data URI nếu có (vd: "data:image/jpeg;base64,...")
            if "," in b64_image:
                b64_image = b64_image.split(",", 1)[1]

            img_bytes = base64.b64decode(b64_image)
            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame  # Trả về None tự động nếu imdecode thất bại
        except Exception as e:
            print(f"[AI Engine][_decode_base64_to_bgr] Lỗi giải mã Base64: {e}")
            return None

    def _undistort(self, frame: np.ndarray) -> np.ndarray:
        """
        Áp dụng giải méo quang học nếu Calibrator đang hoạt động.
        Nếu không, trả về ảnh gốc không thay đổi.
        """
        if self._calibration_enabled and self.calibrator is not None:
            return self.calibrator.undistort_image(frame)
        return frame

    def _get_faces_sorted_by_area(self, frame_bgr: np.ndarray) -> list:
        """
        Chạy InsightFace trên một ảnh BGR, trả về danh sách Face objects
        đã được sắp xếp giảm dần theo diện tích bounding box.
        """
        if self.app is None:
            return []
        faces = self.app.get(frame_bgr)
        if not faces:
            return []

        # Sắp xếp khuôn mặt theo diện tích bbox: (x2-x1)*(y2-y1) lớn → nhỏ
        faces.sort(
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            reverse=True,
        )
        return faces

    def _detect_faces_opencv(self, img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Fallback face detection using OpenCV DNN (Caffe SSD).
        Return list of (x1, y1, x2, y2) bounding boxes.
        """
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

    def _is_live_face(self, face_crop: np.ndarray) -> bool:
        """
        Run MiniFASNet liveness check. Return True if liveness score > 0.5 (live).
        Always returns True if anti-spoof model is not loaded.
        """
        if self.anti_spoof_session is None:
            return True
        try:
            # Preprocess: resize to 80x80, normalize to [0,1]
            img = cv2.resize(face_crop, (80, 80))
            img = img.astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))[np.newaxis, ...]  # NCHW
            input_name = self.anti_spoof_session.get_inputs()[0].name
            out = self.anti_spoof_session.run(None, {input_name: img})[0]
            # Model outputs a single probability of "live"
            return float(out.squeeze()) > 0.5
        except Exception as e:
            print(f"[AI Engine][_is_live_face] Lỗi anti-spoof: {e}")
            return True  # Graceful: cho qua nếu model lỗi

    # ==========================================================================
    # PUBLIC API
    # ==========================================================================

    def evaluate_fiqa(self, face_crop_bgr: np.ndarray) -> float:
        """
        FIQA – Đánh giá chất lượng khuôn mặt (Face Image Quality Assessment).

        Thuật toán: Laplacian Variance – đo độ sắc nét của ảnh.
        Càng sắc nét → Variance càng cao → Score càng gần 1.0.

        Args:
            face_crop_bgr: Vùng ảnh khuôn mặt đã được cắt (BGR NumPy array).

        Returns:
            float: Điểm chất lượng từ 0.0 (rất mờ) đến 1.0 (rất nét).
        """
        if face_crop_bgr is None or face_crop_bgr.size == 0:
            return 0.0

        gray = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Chuẩn hoá về [0, 1] với ngưỡng tham chiếu 200.0 (webcam thông thường)
        score = laplacian_var / 200.0
        return float(min(score, 1.0))

    def extract_embedding(self, img_rgb: np.ndarray) -> list | None:
        """
        Trích xuất vector đặc trưng 512-D từ một ảnh NumPy đã được decode.

        Args:
            img_rgb: Ảnh NumPy định dạng RGB (không phải BGR). InsightFace
                     buffalo_s tương thích với cả RGB lẫn BGR; ở đây ta
                     chuyển sang BGR trước khi đưa vào app.get().

        Returns:
            list[float] độ dài 512 hoặc None nếu không phát hiện được mặt.

        Ghi chú:
            - Khuôn mặt to nhất trong ảnh sẽ được chọn (giả định là nhân vật chính).
            - `normed_embedding` đã được L2-normalize sẵn bởi InsightFace.
        """
        try:
            # Chuyển RGB → BGR cho OpenCV / InsightFace
            frame_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            faces = self._get_faces_sorted_by_area(frame_bgr)

            if not faces:
                return None

            # Lấy khuôn mặt to nhất (phần tử đầu tiên sau khi đã sắp xếp)
            return faces[0].normed_embedding.tolist()

        except Exception as e:
            print(f"[AI Engine][extract_embedding] Lỗi: {e}")
            return None

    def extract_fused_embedding(self, base64_images: list[str]) -> list:
        """
        Mean Aggregation (Pha Đào tạo – Enrollment):
        Nhận vào 10–15 ảnh Base64 của cùng 1 người, tổng hợp thành
        1 siêu vector (Anchor) duy nhất đại diện cho người đó.

        Luồng xử lý:
            Base64 → BGR → Undistort → InsightFace → normed_embedding
            → np.mean(axis=0) → L2-Normalization → Anchor Vector 512-D

        Args:
            base64_images: Danh sách chuỗi Base64 của ảnh khuôn mặt đào tạo.

        Returns:
            list[float] độ dài 512 (Anchor Vector đã chuẩn hoá L2).

        Raises:
            ValueError: Nếu không trích xuất được embedding hợp lệ từ bất kỳ ảnh nào.
        """
        embeddings: list[np.ndarray] = []

        for idx, b64 in enumerate(base64_images):
            try:
                # BƯỚC 1: Giải mã Base64 → ảnh BGR
                frame = self._decode_base64_to_bgr(b64)
                if frame is None:
                    print(f"[AI Engine][Enrollment] Ảnh #{idx + 1}: Giải mã thất bại, bỏ qua.")
                    continue

                # BƯỚC 2: Giải méo quang học (nếu được kích hoạt)
                frame = self._undistort(frame)

                # BƯỚC 3: Phát hiện khuôn mặt và sắp xếp theo kích thước
                faces = self._get_faces_sorted_by_area(frame)

                if not faces:
                    print(f"[AI Engine][Enrollment] Ảnh #{idx + 1}: Không phát hiện khuôn mặt.")
                    continue

                # BƯỚC 4: Lấy embedding của khuôn mặt to nhất (nhân vật chính)
                # normed_embedding: vector 512-D đã được L2-normalize bởi InsightFace
                embedding = faces[0].normed_embedding
                embeddings.append(embedding)
                print(f"[AI Engine][Enrollment] Ảnh #{idx + 1}: Trích xuất thành công.")

            except Exception as e:
                print(f"[AI Engine][Enrollment] Ảnh #{idx + 1}: Lỗi xử lý – {e}")
                continue

        if not embeddings:
            raise ValueError(
                "Không thể trích xuất được khuôn mặt hợp lệ từ bất kỳ ảnh đào tạo nào! "
                "Kiểm tra lại chất lượng ảnh đầu vào."
            )

        print(f"[AI Engine][Enrollment] Tổng số frame hợp lệ: {len(embeddings)}/{len(base64_images)}")

        # BƯỚC 5: MEAN AGGREGATION – Tính trung bình tất cả embedding
        arr = np.array(embeddings, dtype=np.float32)       # Shape: (N, 512)
        mean_vec = np.mean(arr, axis=0)                    # Shape: (512,)

        # BƯỚC 6: L2-NORMALIZATION – Đưa vector về mặt cầu đơn vị (unit sphere)
        # Đây là bước quan trọng để phép đo Cosine Distance về sau chính xác
        norm = np.linalg.norm(mean_vec)
        if norm == 0:
            raise ValueError("Vector trung bình có norm bằng 0, không thể chuẩn hoá.")

        anchor_vector = mean_vec / norm                    # Shape: (512,), ||v|| = 1.0
        print("[AI Engine][Enrollment] Anchor Vector tổng hợp thành công.")

        return anchor_vector.tolist()

    def process_attendance_frame(self, b64_image: str, mode: str = "1") -> list:
        """
        Pha Điểm danh (Real-time Inference):
        Xử lý một frame được gửi qua WebSocket, trả về danh sách embedding
        của các khuôn mặt đã qua bộ lọc FIQA và Anti-Spoof.

        Args:
            b64_image: Chuỗi Base64 của frame camera.
            mode: Chế độ xử lý:
                  - "1"   → Chỉ trả về embedding của khuôn mặt to nhất
                             (dùng khi chỉ cần nhận diện 1 người: sinh viên tự điểm danh)
                  - "all" → Trả về tất cả embedding hợp lệ trong khung hình
                             (dùng khi điểm danh toàn lớp qua camera giảng viên)

        Returns:
            list[list[float]]: Danh sách các embedding 512-D, mỗi phần tử là
                               embedding của 1 khuôn mặt hợp lệ đã qua FIQA.
                               Trả về [] nếu không phát hiện được khuôn mặt nào.

        Luồng xử lý:
            Base64 → BGR → Undistort → InsightFace → Lọc diện tích tối thiểu
            → Cắt khuôn mặt → FIQA Score → Anti-Spoof → Lọc ngưỡng → Trả về theo mode
        """
        try:
            # BƯỚC 1: Giải mã Base64 → ảnh BGR
            frame = self._decode_base64_to_bgr(b64_image)
            if frame is None:
                return []

            # BƯỚC 2: Giải méo quang học (Lens Undistortion)
            frame = self._undistort(frame)
            ih, iw = frame.shape[:2]

            # BƯỚC 3: Phát hiện tất cả khuôn mặt trong khung hình
            if self.app:
                faces = self.app.get(frame)
            else:
                # Fallback detection – embeddings will be zero vectors
                bboxes = self._detect_faces_opencv(frame)
                faces = [FakeFace(bbox=b) for b in bboxes]

            if not faces:
                return []

            # BƯỚC 4: Lọc và đánh giá từng khuôn mặt
            face_results: list[dict] = []

            for face in faces:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox

                # Kẹp toạ độ về trong giới hạn ảnh (clamp)
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(iw, x2)
                y2 = min(ih, y2)

                # Bỏ qua khuôn mặt có diện tích quá nhỏ (nhiễu / khuôn mặt xa)
                area = (x2 - x1) * (y2 - y1)
                if area <= 0 or area < MIN_FACE_AREA:
                    continue

                # BƯỚC 5: Cắt vùng khuôn mặt để tính FIQA
                face_crop = frame[y1:y2, x1:x2]
                fiqa_score = self.evaluate_fiqa(face_crop)

                # BƯỚC 6: Bộ lọc FIQA – Bỏ qua ảnh mờ nhòe
                if fiqa_score < FIQA_THRESHOLD:
                    continue

                # BƯỚC 7: Anti-Spoof – Kiểm tra liveness
                if not self._is_live_face(face_crop):
                    continue

                # Lưu embedding và metadata để xử lý theo mode
                face_results.append({
                    "embedding": face.normed_embedding.tolist(),
                    "area": area,
                    "fiqa": fiqa_score,
                })

            if not face_results:
                return []

            # BƯỚC 8: Trả về theo cấu hình Mode
            if mode == "1":
                # Sắp xếp theo diện tích giảm dần → lấy khuôn mặt to nhất (gần camera nhất)
                face_results.sort(key=lambda x: x["area"], reverse=True)
                return [face_results[0]["embedding"]]
            else:
                # mode == "all": Trả về tất cả khuôn mặt hợp lệ
                # Vẫn sắp xếp theo diện tích để kết quả nhất quán
                face_results.sort(key=lambda x: x["area"], reverse=True)
                return [f["embedding"] for f in face_results]

        except Exception as e:
            print(f"[AI Engine][process_attendance_frame] Lỗi không mong muốn: {e}")
            return []


# ==============================================================================
# SINGLETON INSTANCE – Khởi tạo 1 lần duy nhất khi module được import
# ==============================================================================
face_engine = FaceEngine()