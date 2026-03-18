import hashlib
import json

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
