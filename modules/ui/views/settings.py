from nicegui import ui

from data import scrape_all

GDC_OPTIONS = {
    'CMA':  'CMA — China Meteorological Administration',
    'DWD':  'DWD — Deutscher Wetterdienst',
    'ECCC': 'ECCC — Environment and Climate Change Canada',
}


def render(container, state):
    with container:
        ui.label("Settings").classes("page-title")

        with ui.card().classes("settings-card"):
            with ui.card_section():
                ui.label("Global Discovery Catalogue (GDC)").classes('text-h6')
                ui.label(
                    "Select the GDC server used for topic discovery in "
                    "Catalogue Search and Tree Search."
                ).classes('text-body2 text-grey-7')
                radio = ui.radio(GDC_OPTIONS, value=state.gdc).props('inline')

                def on_gdc_changed(e):
                    state.gdc = e.sender.value

                radio.on('update:model-value', on_gdc_changed)

        with ui.card().classes("settings-card"):
            with ui.card_section():
                ui.label("GDC Data").classes('text-h6')
                ui.label(
                    "GDC metadata is fetched once at startup. "
                    "Click Refresh to pull the latest data from all three catalogues."
                ).classes('text-body2 text-grey-7')
                ui.button("Refresh GDC data", icon="refresh").on('click', scrape_all)
