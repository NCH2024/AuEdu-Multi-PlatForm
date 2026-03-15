import os
import warnings 
from pathlib import Path
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient

# Tắt các cảnh báo DeprecationWarning xuất phát từ module supabase
warnings.filterwarnings("ignore", category=DeprecationWarning, module="supabase")

# TÍNH TOÁN ĐƯỜNG DẪN TUYỆT ĐỐI
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def get_supabase() -> AsyncClient:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(f"Chưa tìm thấy hoặc cấu hình sai biến môi trường tại: {ENV_PATH}")
    
    return await acreate_client(SUPABASE_URL, SUPABASE_KEY)