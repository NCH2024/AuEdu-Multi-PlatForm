import flet as ft
from core.theme import PRIMARY_COLOR

class CustomDropdown(ft.Dropdown):
    def __init__(self, label: str, options: list[ft.dropdown.Option], col=None, value=None, on_change=None):
        super().__init__()
        self.label = label
        self.options = options
        self.col = col
        self.value = value
        
        self.on_select = on_change 
        
        self.border_radius = 8
        self.border_color = ft.Colors.with_opacity(0.1, ft.Colors.BLACK)
        self.focused_border_color = PRIMARY_COLOR
        self.bgcolor = ft.Colors.WHITE
        self.color = ft.Colors.BLACK_87 
        
        self.label_style = ft.TextStyle(color=ft.Colors.GREY_600, size=13)
        self.text_size = 13
        
        self.dense = True 
        self.filled = True 
        
        self.menu_height = 250 
        
        self.content_padding = ft.Padding(0,0,0,0)