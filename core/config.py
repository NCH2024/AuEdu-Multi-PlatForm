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

async def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(f"Chưa tìm thấy hoặc cấu hình sai biến môi trường tại: {ENV_PATH}")
    
    return httpx.AsyncClient(
        base_url=f"{SUPABASE_URL}/rest/v1",
        headers=get_headers()
    )

def get_storage_url() -> str:
    """URL gốc để truy cập các object public trong Storage."""
    return f"{SUPABASE_URL}/storage/v1/object/public"