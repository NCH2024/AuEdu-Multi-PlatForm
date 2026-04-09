import cv2

print("⏳ Đang gọi cửa Camera số 0...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Lỗi: Windows hoặc phần cứng đã chặn không cho Python mở Camera!")
else:
    print("✅ THÀNH CÔNG! Camera đã mở. Bấm phím 'q' trên cửa sổ camera để thoát.")
    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow('Test Camera Doc Lap', frame)
        # Bấm 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()