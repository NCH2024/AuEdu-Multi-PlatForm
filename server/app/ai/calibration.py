import cv2
import numpy as np

class CameraCalibrator:
    def __init__(self):
        """
        Tiền xử lý quang học:
        Lưu trữ ma trận nội tại và hệ số biến dạng của camera.
        Ở đây dùng số liệu giả định cho một webcam 1080p góc rộng phổ thông.
        (Thực tế có thể dùng bài toán bàn cờ - chessboard calibration để lấy tham số chuẩn).
        """
        # Giả định độ phân giải mặc định là 1080p (Full HD)
        self.image_size = (1920, 1080)
        
        # Tiêu cự (Focal length) thường bằng khoảng 80-90% chiều rộng ảnh đối với webcam phổ thông
        focal_length = self.image_size[0] * 0.8
        center_x = self.image_size[0] / 2.0
        center_y = self.image_size[1] / 2.0
        
        # Ma trận nội tại (Intrinsic matrix)
        self.camera_matrix = np.array([
            [focal_length, 0, center_x],
            [0, focal_length, center_y],
            [0, 0, 1]
        ], dtype=np.float32)
        
        # Hệ số biến dạng (Distortion coefficients) [k1, k2, p1, p2, k3]
        # Webcam góc rộng thường bị méo gối (barrel distortion) nên k1 âm.
        self.dist_coeffs = np.array([-0.25, 0.08, 0.0, 0.0, -0.01], dtype=np.float32)

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
