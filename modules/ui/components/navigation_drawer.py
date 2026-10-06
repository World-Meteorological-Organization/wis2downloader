import os

from nicegui import ui

from i18n import current_lang, t
from prefs import get_pref, set_pref

DOCS_BASE_URL = 'https://world-meteorological-organization.github.io/wis2downloader'


NAV_ITEMS = [
    ('dashboard', 'nav.dashboard', 'dashboard'),
    ('catalogue', 'nav.catalogue', 'search'),
    ('tree',      'nav.tree',      'account_tree'),
    ('manual',    'nav.manual',    'edit_note'),
    ('manage',    'nav.manage',    'manage_history'),
    ('settings',  'nav.settings',  'settings'),
]


def docs_url() -> str:
    """Online docs in the UI language, for the version set at image build (default: latest)."""
    version = os.getenv('WIS2DOWNLOADER_DOCS_VERSION', 'latest')
    return f'{DOCS_BASE_URL}/{version}/{current_lang()}/index.html'


def build_nav_drawer(layout, on_navigate):
    is_mini = get_pref('nav_mini') == '1'
    props = f"{'mini ' if is_mini else ''}width=250 behavior=desktop"

    with ui.left_drawer(value=True).props(props) as drawer:
        layout.nav_drawer = drawer
        with ui.list().props('dense padding'):
            for view_id, label_key, icon in NAV_ITEMS:
                label = t(label_key)
                with ui.item(on_click=lambda v=view_id: on_navigate(v)) \
                        .props(f'clickable v-ripple rounded aria-label="{label}"') \
                        .classes('menu-nav-item'):
                    with ui.item_section().props('avatar'):
                        ui.icon(icon)
                    with ui.item_section().classes('q-mini-drawer-hide'):
                        ui.item_label(label)

            # Docs are online, not part of the app: open them in a new tab
            label = t('nav.help')
            with ui.item().props(f'clickable v-ripple rounded href="{docs_url()}" target="_blank" '
                                 f'rel="noopener" aria-label="{label}"') \
                    .classes('menu-nav-item'):
                with ui.item_section().props('avatar'):
                    ui.icon('help_outline')
                with ui.item_section().classes('q-mini-drawer-hide'):
                    ui.item_label(label)
                with ui.item_section().props('side').classes('q-mini-drawer-hide'):
                    ui.icon('open_in_new', size='xs')

    def toggle_mini():
        nonlocal is_mini
        is_mini = not is_mini
        set_pref('nav_mini', '1' if is_mini else '0')
        if is_mini:
            drawer.props(add='mini')
        else:
            drawer.props(remove='mini')

    return toggle_mini
