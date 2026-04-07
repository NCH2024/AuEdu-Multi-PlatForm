import flet as ft
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR

class CustomDropdown(ft.Dropdown):
    def __init__(self, label: str, options: list[ft.dropdown.Option], col=None, value=None, on_change=None):
        super().__init__()
        self.label = label
        self.options = options
        self.col = col
        self.value = value
        
        self.on_change = on_change 
        
        self.border_radius = 10
        self.border_width = 1
        self.border_color = ft.Colors.BLACK_12
        self.focused_border_color = SECONDARY_COLOR
        self.bgcolor = ft.Colors.GREY_50
        self.color = SECONDARY_COLOR 
        
        self.label_style = ft.TextStyle(color=ft.Colors.GREY_600, size=12, weight=ft.FontWeight.W_500)
        self.text_size = 13
        
        self.dense = True 
        self.filled = True 
        
        self.menu_height = 250 
        self.content_padding = ft.Padding.symmetric(horizontal=15, vertical=10)
        self.icon_enabled_color = SECONDARY_COLOR