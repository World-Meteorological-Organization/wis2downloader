import os
from nicegui import ui

_base = os.getenv("WIS2DOWNLOADER_BASE_URL", "http://localhost")
GRAFANA_URL = os.getenv("WIS2DOWNLOADER_GRAFANA_URL", f"{_base}/grafana")


def render(container):
    with container:
        src = f"{GRAFANA_URL}/d/wis2-downloader-overview?kiosk&theme=light"
        ui.element('iframe').props(f'src="{src}"').classes('grafana-frame')
