import flet as ft

class AppTheme:
    def __init__(self, is_dark: bool = False, palette_type: str = "BLUE"):
        self.is_dark = is_dark
        self.palette_type = palette_type

        # ==========================================
        # 1. MÀU CHUNG (Nền, Chữ, Viền)
        # ==========================================
        self.bg_color = "#121212" if self.is_dark else "#F3F4F6"
        self.surface_color = "#1E1E1E" if self.is_dark else "#FFFFFF"
        self.text_main = "#F9FAFB" if self.is_dark else "#111827"
        self.text_muted = "#9CA3AF" if self.is_dark else "#6B7280"
        self.divider_color = ft.Colors.with_opacity(0.1, ft.Colors.WHITE if self.is_dark else ft.Colors.BLACK)

        # ==========================================
        # 2. CÁC BỘ MÀU (PALETTES)
        # ==========================================
        if self.palette_type == "BLUE":
            self.primary = "#3B82F6" if self.is_dark else "#0450DF"    
            self.secondary = "#1E3A8A" if self.is_dark else "#1E3A8A"  # Xanh đen cho Header/Menu
            self.accent = "#0EA5E9"                                    
            self.surface_variant = "#1E293B" if self.is_dark else "#EFF6FF"
            
        elif self.palette_type == "MONO":
            self.primary = "#F3F4F6" if self.is_dark else "#111827"    
            self.secondary = "#000000" if self.is_dark else "#111827"  # Đen tuyền
            self.accent = "#6B7280"                                    
            self.surface_variant = "#1F2937" if self.is_dark else "#F9FAFB"
            
        elif self.palette_type == "COLORFUL":
            self.primary = "#8B5CF6" if self.is_dark else "#7C3AED"    
            self.secondary = "#312E81" if self.is_dark else "#312E81"  # Tím than
            self.accent = "#10B981"                                    
            self.surface_variant = "#3730A3" if self.is_dark else "#F3E8FF"

# Biến toàn cục lưu trạng thái Theme hiện tại
current_theme = AppTheme(is_dark=False, palette_type="BLUE")

# ==========================================
# CÔNG CỤ DÀN TRANG DUY NHẤT ĐƯỢC PHÉP DÙNG
# ==========================================
def get_flat_container(content: ft.Control, padding=15, expand=False, use_variant_bg=False) -> ft.Container:
    bg = current_theme.surface_variant if use_variant_bg else current_theme.surface_color
    return ft.Container(
        content=content, padding=padding, expand=expand, bgcolor=bg,
        border_radius=12, border=ft.Border.all(1, current_theme.divider_color)
    )

# GIỮ TẠM ĐỂ TƯƠNG THÍCH NGƯỢC VỚI CÁC TRANG CHƯA SỬA
def adaptive_container(page, content, padding=15, expand=False, **kwargs):
    return get_flat_container(content, padding, expand)

def get_glass_container(content, padding=15, expand=False, **kwargs):
    return get_flat_container(content, padding, expand)

PRIMARY_COLOR = "#AEC6CF"
SECONDARY_COLOR = "#0450DF"
ACCENT_COLOR = "#0A456D"
BG_COLOR = "#F5F7FA"
