import os
from nicegui import app, ui, Client
from nicegui.events import KeyEventArguments

from shared import setup_logging
from layout import build_layout
from data import scrape_all
from views import dashboard, catalogue, tree, subscriptions, settings, manual_subscription, help
from components.navigation_drawer import NAV_ITEMS
from i18n import current_lang, is_rtl

setup_logging()

app.add_static_files('/assets', 'assets')
if os.path.isdir('site'):
    app.add_static_files('/docs', 'site')
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
    ui.page_title('wis2downloader')
    client.content.classes(remove='q-pa-md')

    class AppState:
        def __init__(self):
            self.selected_topics = []
            self.current_view = 'dashboard'

    state = AppState()

    def show_view(name):
        state.current_view = name
        layout.content.clear()
        layout.right_sidebar.value = False
        layout.right_sidebar.clear()
        with layout.content:
            if name == 'dashboard':
                dashboard.render(layout.content)
            elif name == 'catalogue':
                catalogue.render(layout.content, state, layout)
            elif name == 'tree':
                tree.render(layout.content, state, layout)
            elif name == 'manual':
                manual_subscription.render(layout.content)
            elif name == 'manage':
                subscriptions.render(layout.content)
            elif name == 'settings':
                settings.render(layout.content)
            elif name == 'help':
                help.render(layout.content)

    def on_language_change(lang: str):
        app.storage.user['lang'] = lang
        app.storage.user['current_view'] = state.current_view
        ui.navigate.reload()

    async def on_connect():
        lang = current_lang()
        direction = 'rtl' if is_rtl() else 'ltr'
        await ui.run_javascript(
            f"document.documentElement.lang = '{lang}';"
            f"document.documentElement.dir = '{direction}';"
        )

    client.on_connect(on_connect)

    _view_ids = [view_id for view_id, _, _ in NAV_ITEMS]

    def handle_key(e: KeyEventArguments):
        # AltGr on Swiss German (and all Windows/Linux keyboards) is sent as
        # Ctrl+Alt — exclude it by requiring ctrl to be unpressed.
        if not e.action.keydown or not e.modifiers.alt or e.modifiers.ctrl:
            return
        if e.key.name in ('1', '2', '3', '4', '5', '6', '7'):
            idx = int(e.key.name) - 1
            if idx < len(_view_ids):
                show_view(_view_ids[idx])

    ui.keyboard(on_key=handle_key)

    layout = build_layout(show_view, on_language_change)
    show_view(app.storage.user.get('current_view', 'dashboard'))


ui.run(storage_secret=os.getenv('STORAGE_SECRET', 'wis2downloader-secret'))
