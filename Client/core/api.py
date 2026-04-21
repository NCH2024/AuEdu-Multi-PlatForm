# Client/core/api.py
import flet as ft
import json
from core.config import get_supabase_client, API_PREFIX

async def get_auth_token() -> str:
    """Đọc và giải mã token từ SharedPreferences"""
    prefs = ft.SharedPreferences()
    user_session_str = await prefs.get("user_session")
    if user_session_str:
        try:
            session_data = json.loads(user_session_str)
            return session_data.get("access_token", "")
        except Exception:
            pass
    return ""

async def api_get(endpoint: str, params: dict = None, use_prefix: bool = False):
    """
    Tự động gắn Token và gọi HTTP GET.
    - use_prefix: Nếu True, sẽ tự thêm '/v1' vào trước endpoint (chuẩn bị cho API versioning).
    """
    client = await get_supabase_client()
    token = await get_auth_token()
    
    headers = client.headers.copy()
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    url = f"{API_PREFIX}{endpoint}" if use_prefix and not endpoint.startswith(API_PREFIX) else endpoint
        
    response = await client.get(url, params=params, headers=headers)
    # response.raise_for_status() # Bỏ comment dòng này nếu muốn tự động văng lỗi khi API tạch (mã >= 400)
    return response

async def api_post(endpoint: str, json_data: dict = None, use_prefix: bool = False):
    """Tự động gắn Token và gọi HTTP POST"""
    client = await get_supabase_client()
    token = await get_auth_token()
    
    headers = client.headers.copy()
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    url = f"{API_PREFIX}{endpoint}" if use_prefix and not endpoint.startswith(API_PREFIX) else endpoint
        
    response = await client.post(url, json=json_data, headers=headers)
    return response

# Có thể viết thêm api_put, api_delete tương tự nếu CSDL có chức năng chỉnh sửa/xoá.