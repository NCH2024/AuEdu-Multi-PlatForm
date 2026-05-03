"""
server/app/core/config.py
=========================
Centralised configuration module.

Reads from environment variables (via .env) with sensible defaults so the
server can always start even when a `.env` file is missing.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Supabase Configuration ────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "public")

# ── AI Quality ────────────────────────────────────
FIQA_THRESHOLD: float = float(os.getenv("FIQA_THRESHOLD", "0.05"))
ANTI_SPOOF_MODEL: str = os.getenv("ANTI_SPOOF_MODEL", "MiniFASNetV2.pth")

# ── WebSocket Queue ──────────────────────────────
MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "8"))
DROP_OLDEST: bool = os.getenv("DROP_OLDEST", "true").lower() == "true"

# ── Camera Calibration ───────────────────────────
CALIBRATION_MODE: str = os.getenv("CALIBRATION_MODE", "auto")
CALIBRATION_DATA: str = os.getenv("CALIBRATION_DATA", "calib.npy")
