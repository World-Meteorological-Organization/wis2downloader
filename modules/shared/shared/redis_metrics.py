"""Redis-backed Prometheus metrics helpers.

Each counter/gauge is stored as a Redis hash:
  Key:   wis2:metrics:{metric_name}
  Field: JSON-encoded label dict (keys sorted for consistency)
  Value: numeric string

HINCRBYFLOAT is atomic, so multiple Celery containers all writing to the
same Redis instance aggregate their metrics naturally with no PID collisions
or shared-filesystem issues.

Usage (in task workers):
    from shared.redis_metrics import incr_counter
    incr_counter('downloads_total', {'cache': 'example.com', 'media_type': 'application/bufr'})

Usage (in the metrics endpoint):
    from shared.redis_metrics import set_gauge, generate_prometheus_text
    set_gauge('celery_queue_length', {'queue_name': 'celery'}, 42)
    text = generate_prometheus_text()
"""

import json

from .redis_client import get_redis_client
from .logging import setup_logging

LOGGER = setup_logging(__name__)

_METRIC_PREFIX = "wis2:metrics:"

# Canonical metric definitions: short name → (prometheus type, HELP text)
# The full exposed name is "wis2downloader_{name}".
METRICS: dict[str, tuple[str, str]] = {
    'notifications_total': (
        'counter',
        'Total number of notifications processed.',
    ),
    'downloads_total': (
        'counter',
        'Total number of files downloaded.',
    ),
    'downloads_bytes_total': (
        'counter',
        'Total number of bytes downloaded.',
    ),
    'skipped_total': (
        'counter',
        'Total number of skipped notifications by reason.',
    ),
    'failed_total': (
        'counter',
        'Total number of failed downloads by reason.',
    ),
    'celery_queue_length': (
        'gauge',
        'Current number of tasks in the Celery default queue.',
    ),
}


def _label_field(labels: dict) -> str:
    """Stable JSON encoding of a label dict for use as a Redis hash field."""
    return json.dumps(labels, sort_keys=True)


def incr_counter(metric: str, labels: dict, amount: float = 1.0) -> None:
    """Atomically increment a Redis-backed counter.

    Args:
        metric: Short metric name (without the wis2downloader_ prefix).
        labels: Label key/value pairs, e.g. {'status': 'success'}.
        amount: Amount to add (default 1).
    """
    try:
        get_redis_client().hincrbyfloat(
            f"{_METRIC_PREFIX}{metric}", _label_field(labels), amount)
    except Exception as exc:
        LOGGER.error(f"Failed to increment metric '{metric}': {exc}")


def set_gauge(metric: str, labels: dict, value: float) -> None:
    """Set a Redis-backed gauge to an absolute value.

    Args:
        metric: Short metric name (without the wis2downloader_ prefix).
        labels: Label key/value pairs.
        value:  The new gauge value.
    """
    try:
        get_redis_client().hset(
            f"{_METRIC_PREFIX}{metric}", _label_field(labels), value)
    except Exception as exc:
        LOGGER.error(f"Failed to set gauge '{metric}': {exc}")


def generate_prometheus_text() -> str:
    """Read all metrics from Redis and return Prometheus text-format output.

    Returns an empty string if Redis is unreachable (Prometheus will treat
    the scrape as failed rather than receiving stale/zero data).
    """
    try:
        redis_client = get_redis_client()
    except Exception as exc:
        LOGGER.error(f"Redis unavailable for metrics generation: {exc}")
        return ""

    lines: list[str] = []

    for name, (mtype, help_text) in METRICS.items():
        key = f"{_METRIC_PREFIX}{name}"
        try:
            samples = redis_client.hgetall(key)
        except Exception as exc:
            LOGGER.error(f"Failed to read metric '{name}' from Redis: {exc}")
            continue

        if not samples:
            continue

        full_name = f"wis2downloader_{name}"
        lines.append(f"# HELP {full_name} {help_text}")
        lines.append(f"# TYPE {full_name} {mtype}")

        for labels_bytes, value_bytes in samples.items():
            try:
                labels = json.loads(labels_bytes.decode())
                value = value_bytes.decode()
                if labels:
                    labels_str = ','.join(f'{k}="{v}"' for k, v in labels.items())
                    lines.append(f'{full_name}{{{labels_str}}} {value}')
                else:
                    lines.append(f'{full_name} {value}')
            except Exception as exc:
                LOGGER.warning(f"Skipping malformed sample for '{name}': {exc}")

        lines.append('')  # blank line between metric families

    return '\n'.join(lines)
