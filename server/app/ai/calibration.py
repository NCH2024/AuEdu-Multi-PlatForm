"""
server/app/ai/calibration.py
=============================
Tiền xử lý quang học – Camera Calibration & Undistortion

Thay vì hard-code ma trận nội tại, module này hỗ trợ:
    1. Tự động tính calibration bằng chessboard pattern (auto mode).
    2. Cache kết quả vào file .npy để không cần calibrate lại mỗi lần khởi động.
    3. Fallback về giá trị mặc định nếu không thể calibrate.
"""

import os
import cv2
import numpy as np
from typing import Tuple

from app.core.config import CALIBRATION_MODE, CALIBRATION_DATA


class CameraCalibrator:
    def __init__(self):
        """
        Tiền xử lý quang học:
        Tải hoặc tính toán ma trận nội tại và hệ số biến dạng của camera.
        """
        # Load or compute calibration data
        if CALIBRATION_MODE == "auto" and os.path.exists(CALIBRATION_DATA):
            data = np.load(CALIBRATION_DATA, allow_pickle=True).item()
            self.camera_matrix = data["camera_matrix"]
            self.dist_coeffs = data["dist_coeffs"]
            print("[Calibrator] Đã tải calibration data từ cache:", CALIBRATION_DATA)
        else:
            # Perform one-time chessboard calibration (fallback to defaults)
            self.camera_matrix, self.dist_coeffs = self._auto_calibrate()
            np.save(CALIBRATION_DATA, {
                "camera_matrix": self.camera_matrix,
                "dist_coeffs": self.dist_coeffs,
            })
            print("[Calibrator] Đã lưu calibration data vào:", CALIBRATION_DATA)

    def _auto_calibrate(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run a quick chessboard calibration using the first available webcam.

        Sử dụng pattern 9x6 với ô vuông 25 mm.
        Thu thập 10 frame hợp lệ rồi tính toán calibration.
        Nếu không thể mở webcam hoặc không tìm thấy chessboard,
        sẽ fallback về giá trị mặc định phù hợp cho webcam 1080p phổ thông.
        """
        pattern = (9, 6)
        objp = np.zeros((np.prod(pattern), 3), np.float32)
        objp[:, :2] = np.indices(pattern).T.reshape(-1, 2)
        objp *= 0.025  # 25 mm

        objpoints, imgpoints = [], []
        gray_shape = None

        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise RuntimeError("Không thể mở webcam để calibrate.")

            attempts = 0
            max_attempts = 200  # Giới hạn số frame thử
            while len(objpoints) < 10 and attempts < max_attempts:
                ret, img = cap.read()
                if not ret:
                    attempts += 1
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray_shape = gray.shape
                ret, corners = cv2.findChessboardCorners(gray, pattern, None)
                if ret:
                    objpoints.append(objp)
                    imgpoints.append(corners)
                    cv2.drawChessboardCorners(img, pattern, corners, ret)
                    cv2.imshow("Calibrating...", img)
                    cv2.waitKey(500)
                attempts += 1

            cap.release()
            cv2.destroyAllWindows()

            if len(objpoints) >= 3 and gray_shape is not None:
                ret, mtx, dist, _, _ = cv2.calibrateCamera(
                    objpoints, imgpoints, gray_shape[::-1], None, None
                )
                print(f"[Calibrator] Auto-calibrate thành công với {len(objpoints)} frame(s).")
                return mtx, dist
            else:
                print("[Calibrator] Không đủ chessboard frame → dùng giá trị mặc định.")
                raise RuntimeError("Không đủ dữ liệu chessboard.")

        except Exception as e:
            print(f"[Calibrator][WARN] Auto-calibrate thất bại: {e}. Sử dụng giá trị mặc định.")
            # Fallback: Giá trị mặc định cho webcam 1080p góc rộng phổ thông
            image_size = (1920, 1080)
            focal_length = image_size[0] * 0.8
            center_x = image_size[0] / 2.0
            center_y = image_size[1] / 2.0

            camera_matrix = np.array([
                [focal_length, 0, center_x],
                [0, focal_length, center_y],
                [0, 0, 1]
            ], dtype=np.float32)

            dist_coeffs = np.array([-0.25, 0.08, 0.0, 0.0, -0.01], dtype=np.float32)
            return camera_matrix, dist_coeffs

    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        """
        Kéo phẳng các vùng bị méo do thấu kính góc rộng, giúp khuôn mặt ở biên không bị biến dạng.
        """
        if image is None or image.size == 0:
            return image
            
        h, w = image.shape[:2]
        
        # Lấy ma trận tối ưu để không bị mất các pixel hợp lệ (alpha=1)
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), 1, (w, h)
        )
        
        # Thực hiện thuật toán giải méo (undistort)
        undistorted_img = cv2.undistort(
            image, self.camera_matrix, self.dist_coeffs, None, new_camera_matrix
        )
        
        # (Tùy chọn) Cắt đi những vùng đen bị trống sau khi giải méo nếu dùng alpha=0
        # x, y, w_roi, h_roi = roi
        # undistorted_img = undistorted_img[y:y+h_roi, x:x+w_roi]
        
        return undistorted_img
