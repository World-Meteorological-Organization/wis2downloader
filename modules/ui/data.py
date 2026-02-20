import httpx
from nicegui import app
from shared import setup_logging

from models.wcmp2 import WCMP2Record

LOGGER = setup_logging(__name__)

GDC_SOURCES = [
    ("https://gdc.wis.cma.cn",          "CMA"),
    ("https://wis2.dwd.de/gdc",          "DWD"),
    ("https://wis2-gdc.weather.gc.ca",   "ECCC"),
]

# Keyed by GDC short name; values are parsed WCMP2Record lists.
# Raw JSON is kept in app.storage.general for caching across restarts.
gdc_records: dict[str, list[WCMP2Record]] = {key: [] for _, key in GDC_SOURCES}


def _parse_features(data: dict) -> list[WCMP2Record]:
    return [WCMP2Record.from_dict(f) for f in data.get('features', [])]


async def scrape_all():
    # Populate from cache first so data is available even if GDCs are unreachable
    for _, key in GDC_SOURCES:
        cached = app.storage.general.get(f'gdc_{key}')
        if cached:
            gdc_records[key] = _parse_features(cached)
            LOGGER.info(f"Loaded cached GDC data for {key}")

    # Then attempt a live refresh
    async with httpx.AsyncClient() as client:
        for url, key in GDC_SOURCES:
            try:
                response = await client.get(
                    f'{url}/collections/wis2-discovery-metadata/items?limit=2000&f=json',
                    timeout=5,
                )
                data = response.json()
                gdc_records[key] = _parse_features(data)
                app.storage.general[f'gdc_{key}'] = data
                LOGGER.info(f"Refreshed GDC data for {key}")
            except Exception as e:
                LOGGER.error(f"Error fetching data from {url}: {e}")
