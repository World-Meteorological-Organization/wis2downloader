from nicegui import app, ui, Client

from shared import setup_logging
from layout import build_header, build_footer
from data import scrape_all
from views import dashboard, catalogue, tree, subscriptions, settings

setup_logging()

app.add_static_files('/assets', 'assets')
ui.add_head_html('<link rel="stylesheet" type="text/css" href="/assets/base.css">', shared=True)

app.on_startup(scrape_all)

app.colors(
    base_100="#FFFFFF",
    base_200="#5D8FCF",
    base_300="#77AEE4",
    base_400="#206AAA",
    primary="#2563eb",
    secondary="#64748b",
    accent="#10b981",
    grey_1="#f8fafc",
    grey_2="#f1f5f9",
)

NAV_ITEMS = [
    ('dashboard', 'Dashboard',            'dashboard'),
    ('catalogue', 'Catalogue Search',     'search'),
    ('tree',      'Tree Search',          'account_tree'),
    ('manage',    'Manage Subscriptions', 'manage_history'),
    ('settings',  'Settings',             'settings'),
]


@ui.page('/')
def main_page(client: Client):
    ui.page_title('WIS2box-Rx')
    client.content.classes(remove='q-pa-md')

    class AppState:
        def __init__(self):
            self.gdc = None              # selected GDC: 'CMA', 'DWD', or 'ECCC'
            self.features = {}
            self.selected_topics = []
            self.selected_datasets = {}
            self.tree_widget = None

    class PageLayout:
        def __init__(self):
            self.content = None
            self.right_sidebar = None
            self.dataset_sidebar = None
            self.home = None

    state = AppState()
    layout = PageLayout()

    is_mini = [True]

    def toggle_mini():
        is_mini[0] = not is_mini[0]
        if is_mini[0]:
            drawer.props(add='mini')
        else:
            drawer.props(remove='mini')

    def show_view(name):
        layout.content.clear()
        layout.right_sidebar.set_value(False)
        layout.right_sidebar.clear()
        layout.dataset_sidebar.clear()
        layout.dataset_sidebar.set_visibility(name in ('catalogue', 'tree'))
        with layout.content:
            if name == 'dashboard':
                dashboard.render(layout.content)
            elif name == 'catalogue':
                catalogue.render(layout.content, state, layout)
            elif name == 'tree':
                tree.render(layout.content, state, layout)
            elif name == 'manage':
                subscriptions.render(layout.content)
            elif name == 'settings':
                settings.render(layout.content, state)

    with ui.left_drawer(value=True).props("mini mini-width=60 width=250") as drawer:
        layout.home = drawer
        ui.button(icon='menu').props('flat round').on('click', toggle_mini)
        with ui.list().props('dense padding'):
            for view_id, label, icon in NAV_ITEMS:
                with ui.item(on_click=lambda v=view_id: show_view(v)) \
                        .props('clickable v-ripple rounded') \
                        .classes('menu-nav-item'):
                    with ui.item_section().props('avatar'):
                        ui.icon(icon)
                    with ui.item_section().classes('q-mini-drawer-hide'):
                        ui.item_label(label)

    build_header()

    with ui.element("div").classes("flex flex-row h-full w-full relative"):
        with ui.element("div").classes("flex-grow min-w-0 bg-base-100 h-full") as content:
            layout.content = content
        with ui.element("div").classes("bg-base-100 p-4 dataset-sidebar") as dataset_sidebar:
            layout.dataset_sidebar = dataset_sidebar

    layout.right_sidebar = ui.right_drawer(value=False).classes("bg-base-100 p-4 right-sidebar")

    build_footer()

    show_view('dashboard')


ui.run(favicon='assets/logo.png')
