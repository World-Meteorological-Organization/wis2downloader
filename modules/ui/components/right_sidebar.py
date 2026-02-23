from nicegui import ui


def build_right_sidebar(layout):
    with ui.right_drawer(value=False).props('overlay bordered width=350').style(
        'padding: 1rem; background-color: #f5f6fa'
    ) as right_drawer:
        layout.right_sidebar = right_drawer
