import sys
import os
import time
import asyncio
import argparse
from typing import List

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import AsyncSessionLocal
from app.services.attendance_service import _get_embeddings_from_frame
from app.services.attendance_cache import attendance_cache
from app.db.models import FaceEmbedding, DiemDanh

def generate_dummy_base64_image():
    # Return a dummy string for benchmark
    return "dummy_base64_string"

async def run_benchmark(tkb_tiet_id: int, num_frames: int, embeddings_per_frame: int):
    print(f"Bắt đầu Benchmark:")
    print(f"- tkb_tiet_id: {tkb_tiet_id}")
    print(f"- Số frame mô phỏng: {num_frames}")
    print(f"- Số embedding/frame: {embeddings_per_frame}")

    async with AsyncSessionLocal() as db:
        # Measure Cache Load
        start_cache = time.perf_counter()
        await attendance_cache.load_class_data(tkb_tiet_id, db)
        cache_duration = (time.perf_counter() - start_cache) * 1000
        print(f"Tải Cache: {cache_duration:.2f} ms")

        latencies = []
        
        # Simulate processing frames
        for i in range(num_frames):
            start_frame = time.perf_counter()
            
            # 1. AI Extraction (Simulated or Real)
            # embeddings = await _get_embeddings_from_frame(dummy_image, "all")
            # For pure backend benchmark, we simulate embeddings
            import numpy as np
            dummy_embeddings = [np.random.rand(512).astype(np.float32).tolist() for _ in range(embeddings_per_frame)]
            
            # 2. Local Matching
            start_match = time.perf_counter()
            matches = []
            for emb in dummy_embeddings:
                match, score = attendance_cache.find_best_match(tkb_tiet_id, emb)
                if match:
                    matches.append((match.sv_id, score))
            match_duration = (time.perf_counter() - start_match) * 1000

            # 3. Bulk Upsert
            start_upsert = time.perf_counter()
            if matches:
                from app.services.attendance_service import bulk_upsert_attendance
                from datetime import date
                await bulk_upsert_attendance(
                    sv_ids=[m[0] for m in matches],
                    tkb_tiet_id=tkb_tiet_id,
                    attend_date=date.today(),
                    db=db,
                    created_by=1
                )
            upsert_duration = (time.perf_counter() - start_upsert) * 1000

            frame_duration = (time.perf_counter() - start_frame) * 1000
            latencies.append(frame_duration)
            
        # Clear Cache
        attendance_cache.clear_class_data(tkb_tiet_id)

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
        avg = sum(latencies) / len(latencies) if latencies else 0

        print(f"\nKết quả Benchmark:")
        print(f"Avg Latency: {avg:.2f} ms")
        print(f"P95 Latency: {p95:.2f} ms")
        print(f"P99 Latency: {p99:.2f} ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tkb_tiet_id", type=int, default=1)
    parser.add_argument("--frames", type=int, default=50)
    parser.add_argument("--faces", type=int, default=20)
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.tkb_tiet_id, args.frames, args.faces))
