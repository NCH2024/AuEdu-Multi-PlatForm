-- AuEdu Initial System Configuration
-- Run this script to populate the system_config table with default values

-- Note: 'value' column is JSON, so strings must be double-quoted.
INSERT INTO system_config (key, value, description) VALUES
('server_api_url', '"http://127.0.0.1:8000/"', 'Địa chỉ API của máy chủ chính'),
('supabase_url', '"https://your-project.supabase.co"', 'URL kết nối Supabase'),
('supabase_key', '"your-anon-key"', 'Khóa Public Anon Key của Supabase'),
('supabase_bucket', '"auedu-bucket"', 'Tên bucket lưu trữ ảnh'),
('ai_threshold', '0.6', 'Ngưỡng nhận diện khuôn mặt (Cosine Similarity)'),
('fiqa_threshold', '30', 'Ngưỡng chất lượng ảnh khuôn mặt (Face Image Quality)'),
('home_cache_ttl', '"300"', 'Thời gian cache trang chủ (giây)'),
('schedule_cache_ttl', '"21600"', 'Thời gian cache lịch dạy (giây)'),
('stats_cache_ttl', '"86400"', 'Thời gian cache thống kê (giây)'),
('session_timeout', '"3600"', 'Thời gian hết hạn phiên làm việc (giây)'),
('app_version', '"1.0.0"', 'Phiên bản ứng dụng')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    description = EXCLUDED.description;
