from nicegui import ui


def build_header():
    with ui.header(elevated=True).classes("header-bg"):
        ui.image('assets/wmo-banner.png').props("fit=cover").classes("header-banner")
        ui.image('assets/wmo-foot.png').classes("header-divider")
        ui.image('assets/logo.png').classes("header-logo")


def build_footer():
    with ui.footer().classes("bg-base-400"):
        ui.image('assets/wmo-foot.png').classes("footer-divider")
        ui.label("© 2026 World Meteorological Organization").classes("footer-copyright")
