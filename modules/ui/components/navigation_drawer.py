from nicegui import app, ui

from i18n import t


NAV_ITEMS = [
    ('dashboard', 'nav.dashboard', 'dashboard'),
    ('catalogue', 'nav.catalogue', 'search'),
    ('tree',      'nav.tree',      'account_tree'),
    ('manual',    'nav.manual',    'edit_note'),
    ('manage',    'nav.manage',    'manage_history'),
    ('settings',  'nav.settings',  'settings'),
    ('help',      'nav.help',      'help_outline'),
]


def build_nav_drawer(layout, on_navigate):
    is_mini = app.storage.user.get('is_mini', True)
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

    def toggle_mini():
        app.storage.user['is_mini'] = not app.storage.user.get('is_mini', True)
        if app.storage.user['is_mini']:
            drawer.props(add='mini')
        else:
            drawer.props(remove='mini')

    return toggle_mini
