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

SERVER_API_URL = "http://100.64.0.10:8000/"

import flet as ft
import json

def get_headers(token: str = None):
    auth_token = token if token else SUPABASE_KEY
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

_shared_client: httpx.AsyncClient | None = None

def reset_client(new_url: str = None):
    """Xóa client cũ để force tạo lại với URL mới."""
    global _shared_client, SERVER_API_URL
    if new_url:
        SERVER_API_URL = new_url
    if _shared_client:
        _shared_client = None

async def get_supabase_client() -> httpx.AsyncClient:
    global _shared_client
    
    # 1. Lấy token thực tế từ SharedPreferences (nếu đã đăng nhập)
    token = SUPABASE_KEY
    try:
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session = json.loads(session_str)
            token = session.get("access_token", SUPABASE_KEY)
    except Exception:
        pass

    # 2. Kiểm tra nếu client hiện tại dùng token cũ, cần reset
    if _shared_client:
        current_auth = _shared_client.headers.get("Authorization")
        if current_auth != f"Bearer {token}":
            _shared_client = None

    # 3. Khởi tạo client nếu cần
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            base_url=SERVER_API_URL,
            headers=get_headers(token),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            timeout=httpx.Timeout(10.0),
            follow_redirects=True
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