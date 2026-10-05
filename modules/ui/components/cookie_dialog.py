from typing import Callable

from nicegui import ui

from i18n import t
import prefs


def show_cookie_dialog(current_prefs: Callable[[], dict[str, str]]) -> None:
    """Ask once per visit whether preference cookies may be stored; must be answered to continue."""
    with ui.dialog().props('persistent') as dialog, ui.card().classes('dialog-cookies'):
        ui.label(t('cookies.title')).classes('sidebar-title')
        ui.label(t('cookies.text')).classes('text-body2')
        with ui.row().classes('w-full justify-end gap-2'):
            def on_decline():
                prefs.decline()
                dialog.close()

            def on_accept():
                prefs.accept(current_prefs())
                dialog.close()

            ui.button(t('btn.decline'), icon='close').props('flat').on('click', on_decline)
            ui.button(t('btn.accept'), icon='check_circle').props('color=primary').on('click', on_accept)
    dialog.open()
