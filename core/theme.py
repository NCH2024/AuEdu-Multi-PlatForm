import flet as ft

class AppTheme:
    def __init__(self, is_dark: bool = False, palette_type: str = "BLUE"):
        self.update_theme(is_dark, palette_type)

    def update_theme(self, is_dark: bool, palette_type: str):
        self.is_dark = is_dark
        self.palette_type = palette_type

        # ==========================================
        # 1. MÀU CHUNG (Nền, Chữ, Viền) 
        # ==========================================
        self.bg_color = "#121212" if self.is_dark else "#F9FAFB"
        self.surface_color = "#1E1E1E" if self.is_dark else "#FFFFFF"
        self.text_main = "#F9FAFB" if self.is_dark else "#111827"
        self.text_muted = "#9CA3AF" if self.is_dark else "#6B7280"
        self.divider_color = ft.Colors.with_opacity(0.1, ft.Colors.WHITE if self.is_dark else ft.Colors.BLACK)

        # ==========================================
        # 2. 4 BỘ MÀU (PALETTES) ĐÃ TỐI ƯU TƯƠNG PHẢN CHO DARK MODE
        # ==========================================
        if self.palette_type == "PINK": # Hồng phấn ngọt ngào
            self.primary = "#F472B6" if self.is_dark else "#EC4899"    
            # Dark Mode: Đổi từ đỏ mận sậm sang màu Hồng phấn siêu sáng
            self.secondary = "#FBCFE8" if self.is_dark else "#BE185D" 
            self.accent = "#F9A8D4" if self.is_dark else "#F472B6"
            self.surface_variant = "#2D1B2E" if self.is_dark else "#FDF2F8"

        elif self.palette_type == "BLUE": # Xanh dương tươi (Mặc định)
            self.primary = "#3B82F6" if self.is_dark else "#2563EB"    
            # Dark Mode: Đổi từ xanh đen sậm sang Xanh da trời sáng
            self.secondary = "#93C5FD" if self.is_dark else "#1D4ED8" 
            self.accent = "#60A5FA" if self.is_dark else "#3B82F6"
            self.surface_variant = "#1E293B" if self.is_dark else "#EFF6FF"
            
        elif self.palette_type == "GREEN": # Xanh lá pastel
            self.primary = "#34D399" if self.is_dark else "#10B981"    
            # Dark Mode: Đổi từ xanh rêu sậm sang Xanh mint (bạc hà) sáng
            self.secondary = "#6EE7B7" if self.is_dark else "#047857" 
            self.accent = "#A7F3D0" if self.is_dark else "#34D399"
            self.surface_variant = "#1C2A24" if self.is_dark else "#ECFDF5"

        elif self.palette_type == "MONO": # Đen trắng tối giản
            self.primary = "#F3F4F6" if self.is_dark else "#111827"    
            # Dark Mode: Đổi từ đen tuyền sang Trắng tinh khiết
            self.secondary = "#FFFFFF" if self.is_dark else "#000000" 
            self.accent = "#D1D5DB" if self.is_dark else "#6B7280"
            self.surface_variant = "#1F2937" if self.is_dark else "#F3F4F6"

# CHỈ KHỞI TẠO 1 LẦN DUY NHẤT
current_theme = AppTheme(is_dark=False, palette_type="BLUE")

def get_flat_container(content: ft.Control, padding=15, expand=False, use_variant_bg=False) -> ft.Container:
    bg = current_theme.surface_variant if use_variant_bg else current_theme.surface_color
    return ft.Container(
        content=content, padding=padding, expand=expand, bgcolor=bg,
        border_radius=12, border=ft.Border.all(1, current_theme.divider_color)
    )

def adaptive_container(page, content, padding=15, expand=False, **kwargs):
    return get_flat_container(content, padding, expand)

def get_glass_container(content, padding=15, expand=False, **kwargs):
    return get_flat_container(content, padding, expand)

# Hỗ trợ tương thích ngược
PRIMARY_COLOR = current_theme.primary
SECONDARY_COLOR = current_theme.secondary
ACCENT_COLOR = current_theme.accent
BG_COLOR = current_theme.bg_color