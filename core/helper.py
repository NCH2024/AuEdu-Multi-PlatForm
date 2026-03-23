import hashlib
import json
import re
from core.config import SUPABASE_URL

# HELPER [Tạo hash dữ liệu cache để so khớp]
def hash_data(data):
    try:
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    except:
        return ""

def safe_json_load(data_str):
    try:
        return json.loads(data_str) if data_str else None
    except:
        return None

def process_image_url(url: str, bucket_name: str = "images") -> str:
    # Bắt mọi trường hợp None, rỗng hoặc khoảng trắng
    if not url or not str(url).strip() or str(url).strip() == "None":
        return "icon.png"
    
    url = str(url).strip()
    
    # 1. Nếu là ảnh trong storage của Supabase (không có http)
    if not url.startswith("http"):
        return f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{url}"
        
    # 2. Xử lý link Google Drive dạng /file/d/ID/view
    drive_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if drive_match:
        return f"https://drive.google.com/uc?export=view&id={drive_match.group(1)}"
        
    # 3. Xử lý link Google Drive dạng open?id=ID
    drive_id_match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if "drive.google.com" in url and drive_id_match:
        return f"https://drive.google.com/uc?export=view&id={drive_id_match.group(1)}"

    # 4. Là URL bình thường (từ website trường đại học, v.v...)
    return url