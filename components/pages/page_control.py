"""_summary_

Returns:
    _type_: _description_
"""

import flet as ft

def PageControl(route: str, content: ft.Control):
    return ft.View(
                route=route,
                controls=content,
            )
    