from nicegui import ui


def build_page_body(layout):
    with ui.element("div").classes("page-body-row"):
        with ui.element("div").classes("content-area bg-base-100") as content:
            layout.content = content
