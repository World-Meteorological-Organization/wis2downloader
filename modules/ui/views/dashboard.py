import os
from nicegui import ui

GRAFANA_URL = os.getenv("WIS2_GRAFANA_URL", "http://localhost:3000")


def render(container):
    with container:
        ui.element('iframe') \
            .props(f'src="{GRAFANA_URL}/d/wis2-downloader?kiosk&theme=light"') \
            .classes('grafana-frame')
