import os
from nicegui import app, ui, Client

from shared import setup_logging
from layout import build_layout
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

    state = AppState()

    def show_view(name):
        layout.content.clear()
        layout.right_sidebar.set_visibility(False)
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

    layout = build_layout(show_view)
    show_view('dashboard')


ui.run(storage_secret=os.getenv('STORAGE_SECRET', 'wis2box-rx-secret'))
