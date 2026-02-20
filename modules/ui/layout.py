from components.navigation_drawer import build_nav_drawer
from components.header import build_header
from components.footer import build_footer
from components.page_body import build_page_body


class PageLayout:
    def __init__(self):
        self.header = None
        self.footer = None
        self.nav_drawer = None
        self.content = None
        self.dataset_sidebar = None
        self.right_sidebar = None


def build_layout(on_navigate):
    layout = PageLayout()
    toggle_mini = build_nav_drawer(layout, on_navigate)
    build_header(layout, toggle_mini)
    build_page_body(layout)
    build_footer(layout)
    return layout
