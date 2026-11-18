import logging
from pathlib import Path
from urllib.parse import quote

from nicegui import ui

from download_files import (
    DOWNLOADS_ROOT,
    resolve_download_path,
    search_download_files,
    sort_directory_entries,
    sort_download_files,
)
from i18n import t

LOGGER = logging.getLogger(__name__)


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if value < 1024 or unit == 'TB':
            return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024
    return f'{value:.1f} TB'


def render(container, relative_path: str = '', query: str = '', newest_first: bool = True):
    with container:
        ui.label(t('downloads.title')).classes('page-title')

        def show_search():
            container.clear()
            render(container, '', search_input.value.strip(), newest_first)

        def toggle_sort():
            container.clear()
            render(container, relative_path, query, not newest_first)

        def clear_search():
            container.clear()
            render(container, '', '', newest_first)

        with ui.row().classes('items-center full-width q-gutter-xs downloads-controls'):
            search_input = ui.input(
                placeholder=t('downloads.search_hint'),
                value=query,
            ).props('clearable borderless').classes('col downloads-search-input').on(
                'keydown.enter', show_search
            )
            ui.button(
                icon='search',
                on_click=show_search,
            ).props('flat round dense').tooltip(t('downloads.search'))
            ui.button(
                icon='sort',
                on_click=toggle_sort,
            ).props('flat round dense').tooltip(
                t('downloads.show_oldest_first' if newest_first else 'downloads.show_newest_first')
            )
            if query:
                ui.button(
                    icon='close',
                    on_click=clear_search,
                ).props('flat round dense').tooltip(t('downloads.clear_search'))

        try:
            if query:
                root = DOWNLOADS_ROOT.resolve(strict=True)
                files = sort_download_files(search_download_files(query), newest_first, root)
                entries = [(path, path.relative_to(root).as_posix()) for path in files]
            else:
                directory = (
                    DOWNLOADS_ROOT.resolve(strict=True)
                    if not relative_path
                    else resolve_download_path(relative_path)
                )
                if not directory.is_dir():
                    raise FileNotFoundError(relative_path)
                entries = [
                    (entry, (Path(relative_path) / entry.name).as_posix())
                    for entry in sort_directory_entries(
                        [item for item in directory.iterdir() if not item.is_symlink()],
                        newest_first,
                    )
                ]
        except (OSError, RuntimeError, ValueError) as exc:
            LOGGER.warning('Unable to list downloads directory %s: %s', relative_path, exc)
            ui.label(t('downloads.unavailable')).classes('text-negative')
            return

        with ui.row().classes('items-center q-gutter-xs downloads-location'):
            if relative_path and not query:
                parent_path = Path(relative_path).parent.as_posix()
                if parent_path == '.':
                    parent_path = ''
                ui.button(
                    t('downloads.up'),
                    icon='arrow_upward',
                    on_click=lambda: (
                        container.clear(),
                        render(container, parent_path, '', newest_first),
                    ),
                )
            ui.label(
                t('downloads.search_results', query=query) if query
                else f"{t('downloads.root')}/{relative_path}" if relative_path
                else t('downloads.root')
            ).classes('text-body2')
            ui.button(
                t('downloads.refresh'),
                icon='refresh',
                on_click=lambda: (
                    container.clear(),
                    render(container, relative_path, query, newest_first),
                ),
            )

        if not entries:
            empty_message = t('downloads.no_results') if query else t('downloads.empty')
            ui.label(empty_message).classes('text-grey-7 q-mt-md')
            return

        with ui.column().classes('full-width q-mt-md'):
            for entry, child_path in entries:
                if entry.is_dir():
                    with ui.row().classes('items-center full-width'):
                        ui.icon('folder').classes('text-amber')
                        ui.button(
                            entry.name,
                            on_click=lambda path=child_path: (
                                container.clear(), render(container, path, '', newest_first)
                            ),
                        ).props('flat').classes('text-left')
                elif entry.is_file():
                    href = f"/downloads/{quote(child_path, safe='/')}"
                    with ui.row().classes('items-center full-width'):
                        ui.icon('insert_drive_file').classes('text-grey-6')
                        label = child_path if query else entry.name
                        ui.link(label, href, new_tab=True).classes('text-left')
                        ui.label(_format_size(entry.stat().st_size)).classes(
                            'text-caption text-grey-6'
                        )
