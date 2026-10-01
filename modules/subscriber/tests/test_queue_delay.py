import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")

from subscriber import subscriber as subscriber_module  # noqa: E402
from subscriber.subscriber import Subscriber  # noqa: E402

TOPIC = "cache/a/wis2/x/data/core/obs"


@pytest.fixture
def workflow(monkeypatch):
    chain = MagicMock()
    monkeypatch.setattr(subscriber_module, "wis2_download", MagicMock(return_value=chain))
    monkeypatch.setattr(subscriber_module, "incr_counter", lambda *a, **k: None)
    return chain


def _subscriber(queue_delay):
    # Bypass __init__, which connects to the broker
    sub = Subscriber.__new__(Subscriber)
    sub.host = "gb.example"
    sub.queue_delay = queue_delay
    sub.active_subscriptions = {TOPIC: {"pattern": TOPIC, "subscriptions": {"s1": {"id": "s1", "save_path": "x"}}}}
    return sub


def _message():
    return SimpleNamespace(topic=TOPIC, payload=json.dumps({"id": "m1", "properties": {}}).encode())


def test_preferred_broker_queues_immediately(workflow):
    _subscriber(0)._on_message(None, None, _message())

    workflow.apply_async.assert_called_once_with(countdown=None)


def test_other_broker_queues_with_delay(workflow):
    _subscriber(2)._on_message(None, None, _message())

    workflow.apply_async.assert_called_once_with(countdown=2)
