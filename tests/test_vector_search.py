"""
tests/test_vector_search.py
============================
So sánh hiệu suất Vector Search giữa Numpy In-Memory và pgvector (PostgreSQL HNSW).

Mục đích:
    Đánh giá tốc độ tìm kiếm khuôn mặt trong hệ thống AuEdu bằng hai phương pháp:
    1. Numpy dot-product trên RAM (giống attendance_cache.py)
    2. pgvector cosine_distance trên PostgreSQL với HNSW index (tuỳ chọn)

Kịch bản thử nghiệm:
    - Tạo N vector ngẫu nhiên 512 chiều (N = 50, 100, 500, 1000)
    - L2-normalize tất cả vector (giống InsightFace output)
    - Chạy 100 truy vấn tìm kiếm nearest-neighbor cho mỗi N
    - Đo: thời gian trung bình, min, max, P95

Sử dụng:
    # Chỉ test Numpy (mặc định, không cần DB):
    python tests/test_vector_search.py

    # Test cả pgvector (cần PostgreSQL):
    python tests/test_vector_search.py --db-url "postgresql+asyncpg://user:pass@localhost/auedu"

    # Tuỳ chỉnh output:
    python tests/test_vector_search.py --output tests/results/vector_search_report.json

Tác giả: Chanh-Hiep NGUYEN
Ngày tạo: 2026-05-24
"""

import sys
import os
import time
import json
import argparse
import statistics
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# ── Thêm đường dẫn project root để import module server ──
# Không bắt buộc cho script này (chạy standalone) nhưng đảm bảo
# có thể import từ app/ nếu cần trong tương lai.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SERVER_ROOT = _PROJECT_ROOT / "Server"
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_SERVER_ROOT))

import numpy as np

# ── Fix encoding cho Windows console (tránh UnicodeEncodeError) ──
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================================
# HẰNG SỐ CẤU HÌNH
# ============================================================================

# Số chiều embedding (InsightFace ArcFace output = 512)
EMBEDDING_DIM = 512

# Các kích thước tập dữ liệu để benchmark
DEFAULT_SIZES = [50, 100, 500, 1000]

# Số truy vấn cho mỗi kích thước
NUM_QUERIES = 100

# Ngưỡng cosine distance cho nhận diện (giống attendance_cache.py)
MATCH_THRESHOLD = 0.45

# Thư mục kết quả mặc định
DEFAULT_OUTPUT = str(_PROJECT_ROOT / "tests" / "results" / "vector_search_report.json")


# ============================================================================
# 1. NUMPY IN-MEMORY SEARCH (MÔ PHỎNG attendance_cache.py)
# ============================================================================

def generate_normalized_vectors(n: int, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """
    Tạo n vector ngẫu nhiên dim-chiều, đã L2-normalize.
    
    Giải thích:
        InsightFace trả embedding đã L2-normalized, nghĩa là ||v|| = 1.
        Khi đó cosine_similarity(a, b) = dot(a, b) vì:
            cos(θ) = dot(a, b) / (||a|| * ||b||) = dot(a, b) / (1 * 1)
        Và cosine_distance = 1 - cosine_similarity.
    
    Args:
        n: Số lượng vector cần tạo
        dim: Số chiều của mỗi vector
    
    Returns:
        np.ndarray shape (n, dim), dtype float32, mỗi hàng có ||v|| = 1
    """
    # Tạo vector ngẫu nhiên từ phân phối chuẩn
    vectors = np.random.randn(n, dim).astype(np.float32)
    
    # L2-normalize: chia mỗi vector cho norm của nó
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    
    return vectors


def numpy_find_best_match(
    database_vectors: np.ndarray,
    query_vector: np.ndarray,
    threshold: float = MATCH_THRESHOLD,
) -> Tuple[int, float]:
    """
    Tìm vector gần nhất bằng Numpy dot product.
    
    Đây là phiên bản rút gọn của AttendanceCache.find_best_match()
    trong file attendance_cache.py.
    
    Logic giống hệt production:
        1. Tính dot product giữa query và tất cả vector trong DB
        2. distance = 1 - dot_product (cosine distance)
        3. Tìm index có distance nhỏ nhất
        4. Kiểm tra ngưỡng threshold
    
    Args:
        database_vectors: Ma trận (N, 512) chứa tất cả embedding trong cache
        query_vector: Vector truy vấn (512,)
        threshold: Ngưỡng cosine distance tối đa
    
    Returns:
        (best_index, best_distance)
        Nếu best_distance >= threshold -> (-1, best_distance) (không match)
    """
    # Bước 1: Dot product vectorized (O(N * D) nhưng SIMD-optimized)
    dot_products = np.dot(database_vectors, query_vector)
    
    # Bước 2: Cosine distance
    distances = 1.0 - dot_products
    
    # Bước 3: Tìm nearest neighbor
    best_idx = np.argmin(distances)
    best_distance = float(distances[best_idx])
    
    # Bước 4: Kiểm tra ngưỡng
    if best_distance >= threshold:
        return -1, best_distance
    
    return int(best_idx), best_distance


def benchmark_numpy_search(
    n: int,
    num_queries: int = NUM_QUERIES,
) -> Dict[str, Any]:
    """
    Benchmark tốc độ tìm kiếm Numpy cho N vector.
    
    Quy trình:
        1. Tạo N vector L2-normalized (giả lập face embeddings trong cache)
        2. Tạo query vector ngẫu nhiên
        3. Lặp lại num_queries lần, đo thời gian mỗi lần tìm kiếm
        4. Tính thống kê: avg, min, max, P95, P99
    
    Args:
        n: Kích thước database (số embedding)
        num_queries: Số lần truy vấn
    
    Returns:
        Dict chứa kết quả thống kê
    """
    print(f"\n  ▸ Benchmark Numpy với N = {n:,} vectors...")
    
    # Tạo database vectors (mô phỏng cache đã tải)
    db_vectors = generate_normalized_vectors(n, EMBEDDING_DIM)
    
    # Warmup: chạy 5 lần để CPU cache ấm lên
    for _ in range(5):
        q = generate_normalized_vectors(1, EMBEDDING_DIM)[0]
        numpy_find_best_match(db_vectors, q)
    
    # Benchmark chính thức
    latencies_us = []  # Microseconds (µs)
    match_count = 0
    
    for i in range(num_queries):
        # Tạo query vector mới mỗi lần
        query = generate_normalized_vectors(1, EMBEDDING_DIM)[0]
        
        # Đo thời gian tìm kiếm (chỉ tính phần search, không tính tạo vector)
        t_start = time.perf_counter()
        best_idx, best_dist = numpy_find_best_match(db_vectors, query)
        t_end = time.perf_counter()
        
        elapsed_us = (t_end - t_start) * 1_000_000  # Chuyển sang µs
        latencies_us.append(elapsed_us)
        
        if best_idx >= 0:
            match_count += 1
    
    # Tính thống kê
    latencies_sorted = sorted(latencies_us)
    p95_idx = int(len(latencies_sorted) * 0.95) - 1
    p99_idx = int(len(latencies_sorted) * 0.99) - 1
    
    result = {
        "method": "numpy_dot_product",
        "n_vectors": n,
        "n_queries": num_queries,
        "embedding_dim": EMBEDDING_DIM,
        "avg_us": statistics.mean(latencies_us),
        "min_us": min(latencies_us),
        "max_us": max(latencies_us),
        "median_us": statistics.median(latencies_us),
        "p95_us": latencies_sorted[max(p95_idx, 0)],
        "p99_us": latencies_sorted[max(p99_idx, 0)],
        "stdev_us": statistics.stdev(latencies_us) if len(latencies_us) > 1 else 0.0,
        "match_count": match_count,
        "match_rate": match_count / num_queries * 100,
        "all_latencies_us": latencies_us,
    }
    
    print(f"    ✓ Hoàn thành: avg={result['avg_us']:.1f}µs, "
          f"P95={result['p95_us']:.1f}µs, "
          f"max={result['max_us']:.1f}µs")
    
    return result


# ============================================================================
# 2. PGVECTOR DATABASE SEARCH (TUỲ CHỌN - CẦN KẾT NỐI DB)
# ============================================================================

async def benchmark_pgvector_search(
    db_url: str,
    num_queries: int = NUM_QUERIES,
) -> Optional[Dict[str, Any]]:
    """
    Benchmark tốc độ tìm kiếm pgvector trên PostgreSQL.
    
    Sử dụng:
        - HNSW index trên cột embedding
        - Toán tử <=> (cosine distance) của pgvector
        - Truy vấn qua asyncpg (giống production)
    
    Yêu cầu:
        - PostgreSQL đang chạy và có dữ liệu
        - Extension pgvector đã được cài đặt
        - Bảng face_embeddings tồn tại với dữ liệu embedding thật
    
    Args:
        db_url: Connection string (postgresql+asyncpg://...)
        num_queries: Số lần truy vấn
    
    Returns:
        Dict kết quả hoặc None nếu không kết nối được
    """
    try:
        import asyncpg
    except ImportError:
        print("  ⚠ Cần cài đặt: pip install asyncpg")
        return None
    
    # Chuyển đổi SQLAlchemy URL sang asyncpg format
    # postgresql+asyncpg://user:pass@host/db -> postgresql://user:pass@host/db
    raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"\n  ▸ Kết nối đến PostgreSQL...")
    
    try:
        conn = await asyncpg.connect(raw_url)
    except Exception as e:
        print(f"  ✗ Không thể kết nối: {e}")
        return None
    
    try:
        # Kiểm tra pgvector extension
        ext_check = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        )
        if ext_check == 0:
            print("  ✗ pgvector extension chưa được cài đặt!")
            return None
        
        # Đếm số embedding hiện có trong database
        row_count = await conn.fetchval("SELECT COUNT(*) FROM face_embeddings")
        print(f"  ▸ Số embedding trong DB: {row_count:,}")
        
        if row_count == 0:
            print("  ✗ Bảng face_embeddings rỗng, bỏ qua benchmark pgvector.")
            return None
        
        # Kiểm tra xem có HNSW index không
        hnsw_check = await conn.fetchval("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE tablename = 'face_embeddings' 
            AND indexdef ILIKE '%hnsw%'
        """)
        has_hnsw = hnsw_check > 0
        print(f"  ▸ HNSW Index: {'✓ Có' if has_hnsw else '✗ Không (sẽ dùng sequential scan)'}")
        
        # Tạo query vectors ngẫu nhiên
        query_vectors = generate_normalized_vectors(num_queries, EMBEDDING_DIM)
        
        # Warmup: 3 truy vấn đầu tiên
        for i in range(min(3, num_queries)):
            vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vectors[i]) + "]"
            await conn.fetch(f"""
                SELECT sv_id, embedding <=> '{vec_str}'::vector AS distance
                FROM face_embeddings
                ORDER BY embedding <=> '{vec_str}'::vector
                LIMIT 1
            """)
        
        # Benchmark chính thức
        latencies_us = []
        
        for i in range(num_queries):
            vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vectors[i]) + "]"
            
            t_start = time.perf_counter()
            result = await conn.fetch(f"""
                SELECT sv_id, embedding <=> '{vec_str}'::vector AS distance
                FROM face_embeddings
                ORDER BY embedding <=> '{vec_str}'::vector
                LIMIT 1
            """)
            t_end = time.perf_counter()
            
            elapsed_us = (t_end - t_start) * 1_000_000
            latencies_us.append(elapsed_us)
        
        # Tính thống kê
        latencies_sorted = sorted(latencies_us)
        p95_idx = int(len(latencies_sorted) * 0.95) - 1
        p99_idx = int(len(latencies_sorted) * 0.99) - 1
        
        result = {
            "method": "pgvector_cosine_distance",
            "n_vectors": row_count,
            "n_queries": num_queries,
            "embedding_dim": EMBEDDING_DIM,
            "has_hnsw_index": has_hnsw,
            "avg_us": statistics.mean(latencies_us),
            "min_us": min(latencies_us),
            "max_us": max(latencies_us),
            "median_us": statistics.median(latencies_us),
            "p95_us": latencies_sorted[max(p95_idx, 0)],
            "p99_us": latencies_sorted[max(p99_idx, 0)],
            "stdev_us": statistics.stdev(latencies_us) if len(latencies_us) > 1 else 0.0,
            "all_latencies_us": latencies_us,
        }
        
        print(f"    ✓ pgvector: avg={result['avg_us']:.1f}µs, "
              f"P95={result['p95_us']:.1f}µs, "
              f"max={result['max_us']:.1f}µs")
        
        return result
        
    finally:
        await conn.close()


# ============================================================================
# 3. PHÂN TÍCH KHẢ NĂNG MỞ RỘNG (SCALABILITY)
# ============================================================================

def print_scalability_chart(results: List[Dict[str, Any]]):
    """
    In biểu đồ text-based thể hiện quan hệ giữa N và thời gian truy vấn.
    
    Giải thích lý thuyết:
        - Numpy brute-force: O(N × D) nhưng nhờ SIMD vectorization,
          thực tế gần O(1) với N nhỏ (< 10,000) vì CPU cache hiệu quả
        - pgvector HNSW: O(log N) - sublinear nhờ cấu trúc graph
        - Brute-force SQL (không HNSW): O(N) - linear scan
    
    Args:
        results: Danh sách kết quả benchmark Numpy
    """
    print("\n" + "=" * 70)
    print("📊 PHÂN TÍCH KHẢ NĂNG MỞ RỘNG (SCALABILITY ANALYSIS)")
    print("=" * 70)
    
    if not results:
        print("  Không có dữ liệu để phân tích.")
        return
    
    # Lấy giá trị max để scale biểu đồ
    max_avg = max(r["avg_us"] for r in results)
    max_p95 = max(r["p95_us"] for r in results)
    chart_width = 50  # Số ký tự tối đa cho thanh bar
    
    # ── Biểu đồ thời gian trung bình ──
    print("\n  ┌─ Thời gian trung bình (Average Query Time)")
    print("  │")
    
    for r in results:
        n = r["n_vectors"]
        avg = r["avg_us"]
        bar_len = int((avg / max(max_avg, 1)) * chart_width)
        bar = "█" * bar_len
        print(f"  │ N={n:>5,} │ {bar} {avg:>8.1f} µs")
    
    print("  │")
    print(f"  └─{'─' * (chart_width + 25)}")
    
    # ── Biểu đồ P95 ──
    print("\n  ┌─ Thời gian P95 (95th Percentile)")
    print("  │")
    
    for r in results:
        n = r["n_vectors"]
        p95 = r["p95_us"]
        bar_len = int((p95 / max(max_p95, 1)) * chart_width)
        bar = "▓" * bar_len
        print(f"  │ N={n:>5,} │ {bar} {p95:>8.1f} µs")
    
    print("  │")
    print(f"  └─{'─' * (chart_width + 25)}")
    
    # ── Phân tích tỷ lệ tăng ──
    print("\n  ┌─ Phân tích tỷ lệ tăng (Growth Rate)")
    print("  │")
    
    base_avg = results[0]["avg_us"]
    base_n = results[0]["n_vectors"]
    
    for r in results:
        n = r["n_vectors"]
        avg = r["avg_us"]
        ratio_n = n / base_n           # Tỷ lệ tăng kích thước
        ratio_time = avg / base_avg    # Tỷ lệ tăng thời gian
        
        # So sánh với O(N) lý thuyết
        # Nếu ratio_time ≈ 1 -> O(1), nếu ratio_time ≈ ratio_n -> O(N)
        if ratio_n > 1:
            efficiency = ratio_time / ratio_n  # < 1 là tốt (sublinear)
            complexity_guess = "≈O(1)" if efficiency < 0.3 else "≈O(√N)" if efficiency < 0.7 else "≈O(N)"
        else:
            efficiency = 1.0
            complexity_guess = "baseline"
        
        print(f"  │ N={n:>5,} │ Nₓ={ratio_n:>5.1f}x │ Tₓ={ratio_time:>5.2f}x │ "
              f"Hiệu suất: {efficiency:.2f} │ {complexity_guess}")
    
    print("  │")
    print("  │ Ghi chú:")
    print("  │   Nₓ = tỷ lệ tăng kích thước so với baseline")
    print("  │   Tₓ = tỷ lệ tăng thời gian so với baseline")
    print("  │   Hiệu suất = Tₓ/Nₓ (càng thấp càng tốt, <1 = sublinear)")
    print(f"  └─{'─' * (chart_width + 25)}")
    
    # ── So sánh lý thuyết ──
    print("\n  ┌─ Độ phức tạp lý thuyết vs Thực tế")
    print("  │")
    print("  │  Phương pháp         │ Lý thuyết    │ Thực tế (N≤1000)")
    print("  │  ─────────────────── │ ──────────── │ ────────────────")
    print("  │  Numpy dot-product   │ O(N × D)     │ ≈O(1) nhờ SIMD/cache")
    print("  │  pgvector HNSW       │ O(log N)     │ O(log N) + network I/O")
    print("  │  pgvector seq scan   │ O(N × D)     │ O(N) + disk I/O")
    print("  │")
    print("  │  Kết luận cho AuEdu (N < 200 SV/lớp):")
    print("  │  → Numpy in-memory cache là giải pháp TỐI ƯU")
    print("  │  → Không cần pgvector cho real-time matching")
    print("  │  → pgvector phù hợp cho tìm kiếm trên toàn trường (N > 10,000)")
    print(f"  └─{'─' * (chart_width + 25)}")


# ============================================================================
# 4. HIỂN THỊ VÀ LƯU KẾT QUẢ
# ============================================================================

def print_comparison_table(
    numpy_results: List[Dict[str, Any]],
    pgvector_result: Optional[Dict[str, Any]] = None,
):
    """
    In bảng so sánh kết quả benchmark.
    
    Bảng bao gồm:
        - Kích thước N
        - Thời gian trung bình, min, max, P95
        - So sánh Numpy vs pgvector (nếu có)
    """
    print("\n" + "=" * 90)
    print("📋 BẢNG SO SÁNH HIỆU SUẤT VECTOR SEARCH (BENCHMARK RESULTS)")
    print("=" * 90)
    
    # ── Bảng Numpy ──
    print("\n┌─ NUMPY IN-MEMORY (mô phỏng attendance_cache.py)")
    print("├" + "─" * 88 + "┤")
    
    header = (
        f"│ {'N':>6} │ {'Avg (µs)':>10} │ {'Min (µs)':>10} │ "
        f"{'Max (µs)':>10} │ {'Median':>10} │ {'P95 (µs)':>10} │ "
        f"{'P99 (µs)':>10} │"
    )
    print(header)
    print("├" + "─" * 88 + "┤")
    
    for r in numpy_results:
        row = (
            f"│ {r['n_vectors']:>6,} │ {r['avg_us']:>10.1f} │ {r['min_us']:>10.1f} │ "
            f"{r['max_us']:>10.1f} │ {r['median_us']:>10.1f} │ {r['p95_us']:>10.1f} │ "
            f"{r['p99_us']:>10.1f} │"
        )
        print(row)
    
    print("└" + "─" * 88 + "┘")
    
    # ── Bảng pgvector (nếu có) ──
    if pgvector_result:
        print("\n┌─ PGVECTOR (PostgreSQL HNSW)")
        print("├" + "─" * 88 + "┤")
        print(header)
        print("├" + "─" * 88 + "┤")
        
        r = pgvector_result
        row = (
            f"│ {r['n_vectors']:>6,} │ {r['avg_us']:>10.1f} │ {r['min_us']:>10.1f} │ "
            f"{r['max_us']:>10.1f} │ {r['median_us']:>10.1f} │ {r['p95_us']:>10.1f} │ "
            f"{r['p99_us']:>10.1f} │"
        )
        print(row)
        print("└" + "─" * 88 + "┘")
        
        # So sánh trực tiếp
        # Tìm numpy result có N gần nhất với pgvector
        closest_np = min(
            numpy_results,
            key=lambda x: abs(x["n_vectors"] - pgvector_result["n_vectors"]),
        )
        
        print(f"\n  📊 SO SÁNH TRỰC TIẾP (N ≈ {pgvector_result['n_vectors']:,}):")
        speedup = pgvector_result["avg_us"] / max(closest_np["avg_us"], 0.001)
        print(f"     Numpy avg:    {closest_np['avg_us']:>10.1f} µs")
        print(f"     pgvector avg: {pgvector_result['avg_us']:>10.1f} µs")
        print(f"     Tỷ lệ:       Numpy nhanh hơn {speedup:.1f}x" if speedup > 1 
              else f"     Tỷ lệ:       pgvector nhanh hơn {1/speedup:.1f}x")


def save_results(
    numpy_results: List[Dict[str, Any]],
    pgvector_result: Optional[Dict[str, Any]],
    output_path: str,
):
    """
    Lưu kết quả benchmark ra file JSON cho luận văn.
    
    Cấu trúc JSON:
        {
            "metadata": { ... },
            "numpy_results": [ ... ],
            "pgvector_result": { ... },
            "summary": { ... }
        }
    """
    # Tạo thư mục nếu chưa có
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Chuẩn bị dữ liệu (loại bỏ all_latencies cho gọn JSON)
    numpy_clean = []
    for r in numpy_results:
        clean = {k: v for k, v in r.items() if k != "all_latencies_us"}
        numpy_clean.append(clean)
    
    pgvector_clean = None
    if pgvector_result:
        pgvector_clean = {k: v for k, v in pgvector_result.items() if k != "all_latencies_us"}
    
    # Tạo summary
    summary = {
        "best_numpy_avg_us": min(r["avg_us"] for r in numpy_results),
        "worst_numpy_avg_us": max(r["avg_us"] for r in numpy_results),
        "best_numpy_p95_us": min(r["p95_us"] for r in numpy_results),
        "conclusion": (
            "Numpy in-memory cache đáp ứng yêu cầu real-time (<1ms) "
            "cho quy mô lớp học AuEdu (N < 200 sinh viên). "
            "Không cần pgvector cho bài toán matching trong lớp."
        ),
    }
    
    if pgvector_result:
        closest_np = min(
            numpy_results,
            key=lambda x: abs(x["n_vectors"] - pgvector_result["n_vectors"]),
        )
        summary["pgvector_avg_us"] = pgvector_result["avg_us"]
        summary["numpy_vs_pgvector_speedup"] = (
            pgvector_result["avg_us"] / max(closest_np["avg_us"], 0.001)
        )
    
    report = {
        "metadata": {
            "test_name": "Vector Search Performance Benchmark",
            "system": "AuEdu Face Recognition Attendance",
            "timestamp": datetime.now().isoformat(),
            "embedding_dim": EMBEDDING_DIM,
            "num_queries_per_size": NUM_QUERIES,
            "platform": sys.platform,
            "numpy_version": np.__version__,
        },
        "numpy_results": numpy_clean,
        "pgvector_result": pgvector_clean,
        "summary": summary,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n  💾 Kết quả đã lưu tại: {output_path}")


# ============================================================================
# 5. KIỂM TRA TÍNH ĐÚNG ĐẮN (CORRECTNESS VALIDATION)
# ============================================================================

def validate_search_correctness():
    """
    Kiểm tra tính đúng đắn của thuật toán tìm kiếm.
    
    Test cases:
        1. Vector tìm chính nó → distance ≈ 0
        2. Vector trực giao → distance ≈ 1
        3. Vector đối nhau → distance ≈ 2
        4. Tìm đúng nearest neighbor khi biết trước đáp án
    """
    print("\n" + "=" * 70)
    print("🔍 KIỂM TRA TÍNH ĐÚNG ĐẮN (CORRECTNESS VALIDATION)")
    print("=" * 70)
    
    all_passed = True
    
    # ── Test 1: Self-match ──
    # Embedding so khớp với chính nó → distance phải ≈ 0
    db = generate_normalized_vectors(100)
    query = db[42].copy()  # Chọn vector thứ 42
    
    best_idx, best_dist = numpy_find_best_match(db, query, threshold=1.0)
    
    test1_pass = (best_idx == 42 and best_dist < 1e-5)
    status = "✓ PASS" if test1_pass else "✗ FAIL"
    print(f"\n  Test 1 - Self-match:     {status}")
    print(f"           Expected: idx=42, dist≈0.0")
    print(f"           Got:      idx={best_idx}, dist={best_dist:.8f}")
    all_passed = all_passed and test1_pass
    
    # ── Test 2: Orthogonal vectors ──
    # Hai vector trực giao → cosine_similarity = 0 → distance = 1
    v1 = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    v2 = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    v1[0] = 1.0  # Unit vector theo trục x
    v2[1] = 1.0  # Unit vector theo trục y
    
    db_ortho = v1.reshape(1, -1)
    dot_val = float(np.dot(v1, v2))
    dist_val = 1.0 - dot_val
    
    test2_pass = abs(dist_val - 1.0) < 1e-5
    status = "✓ PASS" if test2_pass else "✗ FAIL"
    print(f"\n  Test 2 - Orthogonal:     {status}")
    print(f"           Expected: distance≈1.0")
    print(f"           Got:      distance={dist_val:.8f}")
    all_passed = all_passed and test2_pass
    
    # ── Test 3: Opposite vectors ──
    # Hai vector ngược chiều → cosine_similarity = -1 → distance = 2
    v3 = -v1
    dot_neg = float(np.dot(v1, v3))
    dist_neg = 1.0 - dot_neg
    
    test3_pass = abs(dist_neg - 2.0) < 1e-5
    status = "✓ PASS" if test3_pass else "✗ FAIL"
    print(f"\n  Test 3 - Opposite:       {status}")
    print(f"           Expected: distance≈2.0")
    print(f"           Got:      distance={dist_neg:.8f}")
    all_passed = all_passed and test3_pass
    
    # ── Test 4: Known nearest neighbor ──
    # Tạo DB, chèn vector gần query hơn tất cả
    db_test = generate_normalized_vectors(50)
    # Tạo query và "bạn thân" của nó (thêm nhiễu nhỏ)
    query_vec = generate_normalized_vectors(1)[0]
    # Tạo vector rất gần query (thêm nhiễu 1%)
    close_vec = query_vec + np.random.randn(EMBEDDING_DIM).astype(np.float32) * 0.01
    close_vec = close_vec / np.linalg.norm(close_vec)  # Re-normalize
    
    # Chèn vào vị trí 25
    db_test[25] = close_vec
    
    best_idx, best_dist = numpy_find_best_match(db_test, query_vec, threshold=1.0)
    
    test4_pass = (best_idx == 25)
    status = "✓ PASS" if test4_pass else "✗ FAIL"
    print(f"\n  Test 4 - Known NN:       {status}")
    print(f"           Expected: idx=25 (injected closest neighbor)")
    print(f"           Got:      idx={best_idx}, dist={best_dist:.6f}")
    all_passed = all_passed and test4_pass
    
    # ── Test 5: Threshold filtering ──
    # Tất cả vector xa → không nên match khi threshold thấp
    db_far = generate_normalized_vectors(50)
    query_far = generate_normalized_vectors(1)[0]
    
    # Dùng threshold cực thấp (chỉ match nếu gần như giống hệt)
    best_idx, best_dist = numpy_find_best_match(db_far, query_far, threshold=0.01)
    
    # Vector ngẫu nhiên 512-D gần như chắc chắn có distance > 0.01
    test5_pass = (best_idx == -1)
    status = "✓ PASS" if test5_pass else "✗ FAIL"
    print(f"\n  Test 5 - Threshold:      {status}")
    print(f"           Expected: idx=-1 (no match, threshold=0.01)")
    print(f"           Got:      idx={best_idx}, dist={best_dist:.6f}")
    all_passed = all_passed and test5_pass
    
    # ── Tổng kết ──
    print(f"\n  {'═' * 40}")
    if all_passed:
        print("  ✅ TẤT CẢ 5/5 TEST ĐỀU PASS")
    else:
        print("  ❌ CÓ TEST FAIL - Cần kiểm tra lại thuật toán!")
    print(f"  {'═' * 40}")
    
    return all_passed


# ============================================================================
# MAIN - ENTRY POINT
# ============================================================================

def main():
    """
    Hàm chính điều phối toàn bộ benchmark.
    
    Quy trình thực thi:
        1. Parse arguments
        2. Validate correctness (kiểm tra thuật toán đúng)
        3. Benchmark Numpy cho các kích thước N khác nhau
        4. Benchmark pgvector (nếu có --db-url)
        5. Phân tích scalability
        6. In bảng so sánh
        7. Lưu kết quả JSON
    """
    parser = argparse.ArgumentParser(
        description="AuEdu Vector Search Performance Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
    # Chỉ test Numpy (mặc định):
    python tests/test_vector_search.py

    # Test thêm pgvector:
    python tests/test_vector_search.py --db-url "postgresql+asyncpg://user:pass@localhost/auedu"

    # Tuỳ chỉnh kích thước test:
    python tests/test_vector_search.py --sizes 50 100 200 500 1000 2000

    # Tăng số truy vấn cho kết quả chính xác hơn:
    python tests/test_vector_search.py --queries 500
        """,
    )
    
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="PostgreSQL connection string (vd: postgresql+asyncpg://user:pass@localhost/auedu). "
             "Bỏ trống để chỉ test Numpy."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Đường dẫn file JSON kết quả (mặc định: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=DEFAULT_SIZES,
        help=f"Các kích thước N để benchmark (mặc định: {DEFAULT_SIZES})"
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=NUM_QUERIES,
        help=f"Số truy vấn cho mỗi kích thước (mặc định: {NUM_QUERIES})"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Bỏ qua bước kiểm tra tính đúng đắn"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed cho reproducibility (mặc định: 42)"
    )
    
    args = parser.parse_args()
    
    # ── Thiết lập random seed cho kết quả tái tạo được ──
    np.random.seed(args.seed)
    
    # ── Header ──
    print("=" * 70)
    print("  AuEdu Vector Search Performance Benchmark")
    print("  So sánh hiệu suất tìm kiếm Numpy In-Memory vs pgvector")
    print("=" * 70)
    print(f"  Thời gian:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Embedding dim: {EMBEDDING_DIM}")
    print(f"  Kích thước N:  {args.sizes}")
    print(f"  Số truy vấn:   {args.queries}")
    print(f"  Random seed:   {args.seed}")
    print(f"  pgvector DB:   {'Có (' + args.db_url + ')' if args.db_url else 'Không (chỉ test Numpy)'}")
    print(f"  Output:        {args.output}")
    print("=" * 70)
    
    # ── Bước 1: Kiểm tra tính đúng đắn ──
    if not args.skip_validation:
        correctness_ok = validate_search_correctness()
        if not correctness_ok:
            print("\n⚠ Thuật toán có lỗi! Dừng benchmark.")
            sys.exit(1)
    
    # ── Bước 2: Benchmark Numpy ──
    print("\n" + "=" * 70)
    print("⚡ BENCHMARK NUMPY IN-MEMORY SEARCH")
    print("=" * 70)
    
    numpy_results = []
    for n in args.sizes:
        result = benchmark_numpy_search(n, num_queries=args.queries)
        numpy_results.append(result)
    
    # ── Bước 3: Benchmark pgvector (tuỳ chọn) ──
    pgvector_result = None
    if args.db_url:
        print("\n" + "=" * 70)
        print("🐘 BENCHMARK PGVECTOR (PostgreSQL)")
        print("=" * 70)
        
        import asyncio
        pgvector_result = asyncio.run(
            benchmark_pgvector_search(args.db_url, num_queries=args.queries)
        )
    
    # ── Bước 4: Phân tích scalability ──
    print_scalability_chart(numpy_results)
    
    # ── Bước 5: In bảng so sánh ──
    print_comparison_table(numpy_results, pgvector_result)
    
    # ── Bước 6: Lưu kết quả ──
    save_results(numpy_results, pgvector_result, args.output)
    
    # ── Kết luận ──
    print("\n" + "=" * 70)
    print("📝 KẾT LUẬN")
    print("=" * 70)
    
    best_avg = min(r["avg_us"] for r in numpy_results)
    worst_avg = max(r["avg_us"] for r in numpy_results)
    worst_p95 = max(r["p95_us"] for r in numpy_results)
    
    print(f"""
    1. Numpy In-Memory Search:
       • Thời gian trung bình: {best_avg:.1f} - {worst_avg:.1f} µs
       • P95 cao nhất: {worst_p95:.1f} µs
       • Kết luận: {"✓ Đáp ứng real-time (<1ms)" if worst_p95 < 1000 else "⚠ Có thể cần tối ưu"}
    """)
    
    if pgvector_result:
        print(f"""
    2. pgvector (PostgreSQL):
       • Thời gian trung bình: {pgvector_result['avg_us']:.1f} µs
       • HNSW Index: {'Có' if pgvector_result.get('has_hnsw_index') else 'Không'}
       • N trong DB: {pgvector_result['n_vectors']:,}
        """)
    
    print(f"""
    Khuyến nghị cho AuEdu:
       • Sử dụng Numpy in-memory cache cho điểm danh real-time trong lớp
       • Giữ nguyên thiết kế AttendanceCache (attendance_cache.py)
       • pgvector chỉ cần cho: backup, tìm kiếm cross-class, báo cáo
    """)
    
    print("=" * 70)
    print("  Benchmark hoàn tất! ✓")
    print("=" * 70)


if __name__ == "__main__":
    main()
