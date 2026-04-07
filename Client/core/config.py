import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "public")

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

# core/config.py — Thêm connection pool singleton

_shared_client: httpx.AsyncClient | None = None

async def get_supabase_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            base_url=f"{SUPABASE_URL}/rest/v1",
            headers=get_headers(),
            # Giữ kết nối sống, tái dụng TCP connection
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            timeout=httpx.Timeout(10.0)
        )
    return _shared_client

def get_storage_url() -> str:
    """URL gốc để truy cập các object public trong Storage."""
    return f"{SUPABASE_URL}/storage/v1/object/public"