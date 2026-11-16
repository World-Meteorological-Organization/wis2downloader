import json
import os
from unittest.mock import create_autospec

import redis

os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")

from shared import valkey_metrics  # noqa: E402


def test_subscriber_counters_are_exposed(monkeypatch):
    client = create_autospec(redis.Redis, instance=True)
    client.hgetall.side_effect = lambda key: (
        {json.dumps({"broker": "gb"}).encode(): b"3"} if key.endswith(("notifications_received_total",
                                                                       "queue_errors_total")) else {}
    )
    monkeypatch.setattr(valkey_metrics, "get_valkey_client", lambda: client)

    text = valkey_metrics.generate_prometheus_text()

    assert 'wis2downloader_notifications_received_total{broker="gb"} 3' in text
    assert 'wis2downloader_queue_errors_total{broker="gb"} 3' in text
