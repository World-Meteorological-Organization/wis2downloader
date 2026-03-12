import asyncio
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

# Cached result of merging all GDC records. Rebuilt once after scrape_all().
_merged_records: list['MergedRecord'] = []

# Topic hierarchy derived from merged records. Rebuilt once after scrape_all().
_topic_hierarchy: dict = {}

# Set to True once the first successful scrape_all() has completed.
_ready: bool = False


def is_ready() -> bool:
    """Return True once GDC data has been loaded and processed at least once."""
    return _ready


@dataclass
class MergedRecord:
    """A WCMP2Record merged across GDCs, with provenance metadata."""
    record: WCMP2Record
    source_gdcs: list[str] = field(default_factory=list)
    has_discrepancy: bool = False


def merged_records() -> list[MergedRecord]:
    """Return the cached merged record list. Rebuilt by scrape_all()."""
    return _merged_records


def topic_hierarchy() -> dict:
    """Return the cached topic hierarchy. Rebuilt by scrape_all()."""
    return _topic_hierarchy


def _insert_channel(topic_dict: dict, channel: str, record: WCMP2Record) -> None:
    """Insert a channel and its record into the topic hierarchy.

    Builds a nested structure of the form:
      { "cache": { "children": { "a": { "children": { ... "synop": { "datasets": [...] } } } } } }

    A node may have both "children" and "datasets" if one channel is a prefix of another.
    """
    segments = channel.split('/')
    node = topic_dict
    for segment in segments[:-1]:
        entry = node.setdefault(segment, {})
        node = entry.setdefault("children", {})
    leaf = segments[-1]
    node.setdefault(leaf, {}).setdefault("datasets", []).append(record)


def _collect_datasets(node: dict) -> list[WCMP2Record]:
    """Recursively collect all datasets from a hierarchy node and its descendants."""
    datasets = list(node.get("datasets", []))
    for child in node.get("children", {}).values():
        datasets.extend(_collect_datasets(child))
    return datasets


def _build_topic_hierarchy() -> dict:
    topic_dict: dict = {}
    for merged in _merged_records:
        for channel in merged.record.mqtt_channels:
            if channel.startswith('cache/'):
                _insert_channel(topic_dict, channel, merged.record)
                break
    return topic_dict


def get_datasets_for_channel(channel: str) -> list[WCMP2Record]:
    """Return all datasets reachable from the given channel.

    Strips a trailing /# wildcard and navigates the hierarchy, then collects
    all datasets from that node and any descendants.
    """
    segments = channel.replace('/#', '').split('/')
    node = _topic_hierarchy
    for i, segment in enumerate(segments):
        if segment not in node:
            return []
        node = node[segment]
        if i < len(segments) - 1:
            if 'children' not in node:
                return []
            node = node['children']
    return _collect_datasets(node)


def _build_merged_records() -> list[MergedRecord]:
    """Merge WCMP2Records from all GDCs, deduplicating by id.

    Records with the same id are combined. If properties, geometry, or links
    differ between catalogues, has_discrepancy is set to True on the merged
    record. Links are unioned across GDCs so that channel information present
    in any catalogue is preserved on the merged record.
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

                # Merge links: union channels from this GDC into the primary
                # record so that channel data present in any catalogue is kept.
                existing_channels = {lnk.channel for lnk in m.record.links if lnk.channel}
                incoming_channels = {lnk.channel for lnk in rec.links if lnk.channel}
                if incoming_channels != existing_channels:
                    m.has_discrepancy = True
                for lnk in rec.links:
                    if lnk.channel and lnk.channel not in existing_channels:
                        m.record.links.append(lnk)
                        existing_channels.add(lnk.channel)

    return list(seen.values())


def _parse_features(data: dict) -> list[WCMP2Record]:
    return [WCMP2Record.from_dict(f) for f in data.get('features', [])]


async def _fetch_one(
    client: httpx.AsyncClient,
    r,
    url: str,
    key: str,
    force: bool,
) -> None:
    """Fetch (or load from cache) one GDC source and populate gdc_records[key]."""
    cache_key = f"gdc:cache:{key}"

    if r and not force:
        try:
            cached = await r.get(cache_key)
            if cached:
                gdc_records[key] = _parse_features(json.loads(cached))
                LOGGER.info(f"Loaded {key} from Redis cache ({len(gdc_records[key])} records)")
                return
        except Exception as e:
            LOGGER.warning(f"Redis cache read failed for {key}, fetching from HTTP: {e}")

    try:
        response = await client.get(
            f'{url}/collections/wis2-discovery-metadata/items?limit=2000&f=json',
            timeout=5,
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


async def scrape_all(force: bool = False):
    global _merged_records, _topic_hierarchy, _ready

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
            await asyncio.gather(*[
                _fetch_one(client, r, url, key, force)
                for url, key in GDC_SOURCES
            ])
    finally:
        if r:
            await r.aclose()

    _merged_records = _build_merged_records()
    LOGGER.info(f"Merged records built: {len(_merged_records)} unique records")
    _topic_hierarchy = _build_topic_hierarchy()
    LOGGER.info(f"Topic hierarchy built: {len(_topic_hierarchy)} top-level nodes")
    _ready = True


