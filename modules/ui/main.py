import asyncio
from nicegui import app, ui, Client
from nicegui.events import KeyEventArguments

from shared import setup_logging
from shared.config_check import Setting, require_settings
from layout import build_layout
import data as data_module
from data import scrape_all
from views import dashboard, catalogue, tree, subscriptions, settings, manual_subscription
from components.navigation_drawer import NAV_ITEMS
from i18n import current_lang, is_rtl
from prefs import declined, get_pref, has_consent, prefs_url, set_pref
from components.cookie_dialog import show_cookie_dialog

setup_logging()

# Valkey is optional for the UI (GDC cache), so its password is not required here
require_settings('ui', (
    Setting('VALKEY_PORT', integer=True),
    Setting('GDC_CACHE_TTL_SECONDS', integer=True),
))

app.add_static_files('/assets', 'assets')
ui.add_head_html('<link rel="stylesheet" type="text/css" href="/assets/base.css">', shared=True)

_startup_done = False


async def _startup():
    global _startup_done
    if _startup_done:
        return
    _startup_done = True
    asyncio.create_task(scrape_all())

app.on_startup(_startup)

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
            self.selected_dataset_ids = []
            self.current_view = 'dashboard'

    state = AppState()

    _GDC_VIEWS = {'catalogue', 'tree', 'settings'}

    def show_view(name):
        state.current_view = name
        layout.content.clear()
        if layout.right_sidebar:
            layout.right_sidebar.value = False
            layout.right_sidebar.clear()
        with layout.content:
            if name in _GDC_VIEWS and not data_module.is_ready():
                with ui.column().classes('items-center justify-center q-pa-xl full-width'):
                    ui.spinner('dots', size='xl', color='primary')
                ui.timer(0.5, lambda: show_view(name) if data_module.is_ready() else None)
                return
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

    def current_prefs(lang: str | None = None) -> dict[str, str]:
        return {'lang': lang or current_lang(),
                'nav_mini': '1' if 'mini' in layout.nav_drawer.props else '0'}

    async def on_language_change(lang: str):
        # reopen the same view after the reload
        prefs = dict(current_prefs(lang), view=state.current_view)
        if has_consent():
            for name, value in prefs.items():
                set_pref(name, value)
            ui.navigate.reload()
        else:
            ui.navigate.to(prefs_url(prefs))  # nothing stored: carry them in the URL

    async def on_connect():
        lang = current_lang()
        await ui.run_javascript(f"document.documentElement.lang = '{lang}';")
        if is_rtl():
            await ui.run_javascript("document.documentElement.setAttribute('dir', 'rtl');")
        else:
            await ui.run_javascript("document.documentElement.setAttribute('dir', 'ltr');")

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
    view = get_pref('view')
    show_view(view if view in _view_ids else 'dashboard')

    if not has_consent() and not declined():
        show_cookie_dialog(current_prefs)


ui.run(reload=False,
       favicon='assets/logo.png')
