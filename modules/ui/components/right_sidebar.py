from nicegui import ui


def build_right_sidebar(layout):
    drawer = ui.right_drawer  # ui.left_drawer if is_rtl() else ui.right_drawer
    with drawer(value=True).props('overlay bordered width=350').style(
        'padding: 1rem; background-color: #f5f6fa'
    ) as right_drawer:
        layout.right_sidebar = right_drawer
