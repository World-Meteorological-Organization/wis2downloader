from nicegui import ui


def build_footer(layout):
    with ui.footer().classes("bg-base-400") as footer:
        layout.footer = footer
        ui.image('assets/wmo-foot.png').classes("footer-divider")
        ui.label("© 2026 World Meteorological Organization").classes("footer-copyright")
