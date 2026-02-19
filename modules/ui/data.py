import httpx
from shared import setup_logging

LOGGER = setup_logging(__name__)

json_scrapes = {
    "CMA": {},
    "DWD": {},
    "ECCC": {}
}


async def scrape_all():
    async with httpx.AsyncClient() as client:
        for url, key in [
            ("https://gdc.wis.cma.cn", "CMA"),
            ("https://wis2.dwd.de/gdc", "DWD"),
            ("https://wis2-gdc.weather.gc.ca", "ECCC"),
        ]:
            try:
                response = await client.get(
                    f'{url}/collections/wis2-discovery-metadata/items?limit=2000&f=json',
                    timeout=5,
                )
                json_scrapes[key] = response.json()
            except Exception as e:
                LOGGER.error(f"Error fetching data from {url}: {e}")
                json_scrapes[key] = {}
