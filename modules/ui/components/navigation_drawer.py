from nicegui import app, ui


NAV_ITEMS = [
    ('dashboard', 'Dashboard',            'dashboard'),
    ('catalogue', 'Catalogue Search',     'search'),
    ('tree',      'Tree Search',          'account_tree'),
    ('manage',    'Manage Subscriptions', 'manage_history'),
    ('settings',  'Settings',             'settings'),
]


def build_nav_drawer(layout, on_navigate):
    is_mini = app.storage.user.get('is_mini', True)
    props = f"{'mini ' if is_mini else ''}width=250 behavior=desktop"

    with ui.left_drawer(value=True).props(props) as drawer:
        layout.nav_drawer = drawer
        with ui.list().props('dense padding'):
            for view_id, label, icon in NAV_ITEMS:
                with ui.item(on_click=lambda v=view_id: on_navigate(v)) \
                        .props('clickable v-ripple rounded') \
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
