import json
import os
from dataclasses import dataclass, field

import httpx
import redis.asyncio as aioredis
from shared import setup_logging

from models.wcmp2 import WCMP2Record

LOGGER = setup_logging(__name__)

GDC_CACHE_TTL = int(os.getenv("GDC_CACHE_TTL_SECONDS", str(6 * 3600)))

GDC_SOURCES = [
    ("https://gdc.wis.cma.cn",        "CMA"),
    ("https://wis2.dwd.de/gdc",        "DWD"),
    ("https://wis2-gdc.weather.gc.ca", "ECCC"),
]

# Keyed by GDC short name; values are parsed WCMP2Record lists.
gdc_records: dict[str, list[WCMP2Record]] = {key: [] for _, key in GDC_SOURCES}


@dataclass
class MergedRecord:
    """A WCMP2Record merged across GDCs, with provenance metadata."""
    record: WCMP2Record
    source_gdcs: list[str] = field(default_factory=list)
    has_discrepancy: bool = False


def _parse_features(data: dict) -> list[WCMP2Record]:
    return [WCMP2Record.from_dict(f) for f in data.get('features', [])]


async def scrape_all(force: bool = False):
    r = None
    try:
        r = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            socket_connect_timeout=2,
        )
    except Exception as e:
        LOGGER.warning(f"Could not create Redis client, will fetch GDC data from HTTP: {e}")

    try:
        async with httpx.AsyncClient() as client:
            for url, key in GDC_SOURCES:
                cache_key = f"gdc:cache:{key}"

                if r and not force:
                    try:
                        cached = await r.get(cache_key)
                        if cached:
                            gdc_records[key] = _parse_features(json.loads(cached))
                            LOGGER.info(f"Loaded {key} from Redis cache ({len(gdc_records[key])} records)")
                            continue
                    except Exception as e:
                        LOGGER.warning(f"Redis cache read failed for {key}, fetching from HTTP: {e}")

                try:
                    response = await client.get(
                        f'{url}/collections/wis2-discovery-metadata/items?limit=2000&f=json',
                        timeout=30,
                    )
                    data = response.json()
                    gdc_records[key] = _parse_features(data)
                    LOGGER.info(f"Fetched {key} from HTTP ({len(gdc_records[key])} records)")

                    if r:
                        try:
                            await r.set(cache_key, json.dumps(data), ex=GDC_CACHE_TTL)
                        except Exception as e:
                            LOGGER.warning(f"Redis cache write failed for {key}: {e}")
                except Exception as e:
                    LOGGER.error(f"Error fetching {key} GDC data from {url}: {e}")
    finally:
        if r:
            await r.aclose()


def merged_records() -> list[MergedRecord]:
    """Merge WCMP2Records from all GDCs, deduplicating by id.

    Records with the same id are combined. If properties or geometry differ
    between catalogues, has_discrepancy is set to True on the merged record.
    Each MergedRecord carries source_gdcs listing which catalogues contained it.
    """
    seen: dict[str, MergedRecord] = {}

    for _, gdc_key in GDC_SOURCES:
        for rec in gdc_records[gdc_key]:
            if rec.id not in seen:
                seen[rec.id] = MergedRecord(
                    record=rec,
                    source_gdcs=[gdc_key],
                )
            else:
                m = seen[rec.id]
                m.source_gdcs.append(gdc_key)
                if (rec.properties != m.record.properties or
                        rec.geometry != m.record.geometry):
                    m.has_discrepancy = True

    return list(seen.values())
