from nicegui import ui

from data import gdc_records, scrape_all

_GDC_CHIP_COLOURS = {'CMA': 'blue', 'DWD': 'teal', 'ECCC': 'orange'}


def render(container):
    with container:
        ui.label("Settings").classes("page-title")

        with ui.card().classes("settings-card"):
            with ui.card_section():
                ui.label("Global Discovery Catalogues").classes('text-h6')
                ui.label(
                    "Records are fetched from all three GDCs at startup and merged. "
                    "Results are cached in Redis for 6 hours."
                ).classes('text-body2 text-grey-7')
                with ui.row().classes('q-mt-sm q-gutter-sm'):
                    for name, records in gdc_records.items():
                        count = len(records)
                        colour = _GDC_CHIP_COLOURS.get(name, 'grey') if count else 'grey'
                        label = f"{name}: {count} records" if count else f"{name}: not loaded"
                        ui.chip(label, color=colour)
                async def on_refresh():
                    await scrape_all(force=True)

                ui.button("Refresh GDC data", icon="refresh").on('click', on_refresh)
