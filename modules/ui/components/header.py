from nicegui import ui


def build_header(layout, toggle_mini):
    with ui.header(elevated=True).classes("header-bg") as header:
        layout.header = header
        ui.image('assets/wmo-banner.png').props("fit=cover").classes("header-banner")
        ui.image('assets/wmo-foot.png').classes("header-divider")
        ui.image('assets/logo.png').classes("header-logo")
        with ui.row().classes("header-toolbar"):
            ui.button(icon='menu').props('flat round color=white').on('click', toggle_mini)
