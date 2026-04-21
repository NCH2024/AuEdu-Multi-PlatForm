# Client_App/core/config.py
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
API_PREFIX = "/v1"

# SERVER_API_URL = "http://172.14.1.33:8000/" 

SERVER_API_URL = "http://127.0.0.1:8000/" 
# SERVER_API_URL = "http://192.168.1.5:8000/" 

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

_shared_client: httpx.AsyncClient | None = None

async def get_supabase_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            base_url=SERVER_API_URL,
            headers=get_headers(),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            timeout=httpx.Timeout(10.0)
        )
    return _shared_client

def get_storage_url() -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public"

def get_ws_url(tkb_tiet_id: str, token: str) -> str:
    """
    Tự động chuyển đổi HTTP URL sang WS URL và đính kèm Token.
    """
    base_ws = SERVER_API_URL.replace("http://", "ws://").replace("https://", "wss://")
    if base_ws.endswith("/"):
        base_ws = base_ws[:-1]
        
    return f"{base_ws}/api/ws/attendance/{tkb_tiet_id}?token={token}"