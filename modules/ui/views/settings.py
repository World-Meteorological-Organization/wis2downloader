from nicegui import ui

from data import gdc_records, scrape_all
from i18n import t

_GDC_CHIP_COLOURS = {'CMA': 'blue', 'DWD': 'teal', 'ECCC': 'orange'}


def render(container):
    with container:
        ui.label(t('settings.title')).classes("page-title")

        with ui.card().classes("settings-card"):
            with ui.card_section():
                ui.label(t('settings.gdc_section')).classes('text-h6')
                ui.label(t('settings.gdc_desc')).classes('text-body2 text-grey-7')
                with ui.row().classes('q-mt-sm q-gutter-sm'):
                    for name, records in gdc_records.items():
                        count = len(records)
                        colour = _GDC_CHIP_COLOURS.get(name, 'grey') if count else 'grey'
                        label = (
                            t('settings.records', name=name, count=count) if count
                            else t('settings.not_loaded', name=name)
                        )
                        ui.chip(label, color=colour)

                async def on_refresh():
                    await scrape_all(force=True)

                ui.button(t('btn.refresh_gdc'), icon="refresh").on('click', on_refresh)
