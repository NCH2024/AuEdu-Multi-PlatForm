"""
tests/load_test.py
==================
WebSocket Load Test for AuEdu Attendance System

Mô phỏng N sinh viên (mặc định 10) kết nối đồng thời qua WebSocket,
mỗi kết nối gửi frame Base64 giả lập ở 30 FPS.

Đo lường:
    - Round-trip latency trung bình
    - Số frame bị drop bởi queue
    - Độ ổn định hệ thống dưới tải

Sử dụng:
    python tests/load_test.py --url ws://localhost:8000/api/ws/attendance/1 \\
                              --token <JWT_TOKEN> \\
                              --clients 10 \\
                              --fps 30 \\
                              --duration 30

Lưu ý: Script này KHÔNG nằm trong production. .gitignore đã loại *test*.py
"""

import asyncio
import time
import json
import base64
import argparse
import statistics
import numpy as np

try:
    import websockets
except ImportError:
    print("Cần cài đặt: pip install websockets")
    exit(1)


def generate_synthetic_frame(width: int = 640, height: int = 480) -> str:
    """Tạo ảnh JPEG giả lập (nhiễu ngẫu nhiên) dưới dạng Base64."""
    import cv2
    # Tạo ảnh nhiễu ngẫu nhiên
    img = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    # Vẽ hình chữ nhật mô phỏng khuôn mặt
    cx, cy = width // 2, height // 2
    cv2.rectangle(img, (cx - 80, cy - 100), (cx + 80, cy + 100), (180, 220, 255), -1)
    # Encode JPEG
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 50])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


async def client_session(
    client_id: int,
    url: str,
    fps: int,
    duration: float,
    results: dict,
):
    """Mô phỏng 1 sinh viên kết nối WebSocket và gửi frame liên tục."""
    latencies = []
    sent_count = 0
    recv_count = 0
    interval = 1.0 / fps
    end_time = time.monotonic() + duration

    try:
        async with websockets.connect(url, ping_interval=20, ping_timeout=60) as ws:
            print(f"[Client {client_id}] Connected")

            async def receiver():
                nonlocal recv_count
                try:
                    async for msg in ws:
                        recv_count += 1
                except Exception:
                    pass

            recv_task = asyncio.create_task(receiver())

            while time.monotonic() < end_time:
                frame_b64 = generate_synthetic_frame()
                payload = json.dumps({
                    "image": frame_b64,
                    "mode": "1",
                    "date": "2026-04-26",
                    "vitri": f"LoadTest-Client-{client_id}",
                })

                t0 = time.monotonic()
                await ws.send(payload)
                sent_count += 1

                # Tính latency từ lúc gửi đến khi nhận được response tiếp theo
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    latency = time.monotonic() - t0
                    latencies.append(latency)
                except asyncio.TimeoutError:
                    pass  # Frame bị drop hoặc AI chưa xử lý xong

                # Đợi đúng interval để đạt FPS mong muốn
                elapsed = time.monotonic() - t0
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)

            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        print(f"[Client {client_id}] Error: {e}")

    results[client_id] = {
        "sent": sent_count,
        "recv": recv_count,
        "latencies": latencies,
    }
    print(f"[Client {client_id}] Done – sent={sent_count}, recv={recv_count}")


async def main():
    parser = argparse.ArgumentParser(description="AuEdu WebSocket Load Test")
    parser.add_argument("--url", required=True, help="WebSocket URL (e.g. ws://localhost:8000/api/ws/attendance/1?token=...)")
    parser.add_argument("--token", default="", help="JWT token (appended as ?token=<value> if not in URL)")
    parser.add_argument("--clients", type=int, default=10, help="Number of concurrent clients")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second per client")
    parser.add_argument("--duration", type=float, default=30, help="Test duration in seconds")
    args = parser.parse_args()

    url = args.url
    if args.token and "token=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}token={args.token}"

    print("=" * 60)
    print(f"AuEdu WebSocket Load Test")
    print(f"  URL:       {url}")
    print(f"  Clients:   {args.clients}")
    print(f"  FPS:       {args.fps}")
    print(f"  Duration:  {args.duration}s")
    print("=" * 60)

    results = {}
    tasks = [
        client_session(i, url, args.fps, args.duration, results)
        for i in range(args.clients)
    ]

    await asyncio.gather(*tasks)

    # ── Aggregate Results ──
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    all_latencies = []
    total_sent = 0
    total_recv = 0

    for cid, data in sorted(results.items()):
        total_sent += data["sent"]
        total_recv += data["recv"]
        all_latencies.extend(data["latencies"])

    dropped_estimate = total_sent - total_recv
    avg_lat = statistics.mean(all_latencies) if all_latencies else float("nan")
    p95_lat = (
        sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        if all_latencies
        else float("nan")
    )

    print(f"  Total frames sent:     {total_sent}")
    print(f"  Total responses recv:  {total_recv}")
    print(f"  Estimated drops:       {dropped_estimate}")
    print(f"  Avg latency:           {avg_lat * 1000:.1f} ms")
    print(f"  P95 latency:           {p95_lat * 1000:.1f} ms")
    print(f"  Drop rate:             {dropped_estimate / max(total_sent, 1) * 100:.1f}%")
    print("=" * 60)

    if dropped_estimate / max(total_sent, 1) < 0.5:
        print("✓ System STABLE under load (drop rate < 50%)")
    else:
        print("✗ System UNSTABLE – consider increasing MAX_QUEUE_SIZE or adding workers")


if __name__ == "__main__":
    asyncio.run(main())
