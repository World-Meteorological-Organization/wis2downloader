import json
import os
from unittest.mock import create_autospec

import redis

os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")

from shared import DEFAULT_QUEUE  # noqa: E402
from subscriber.manager import load_persisted_subscriptions  # noqa: E402
from subscriber.subscriber import Subscriber  # noqa: E402


def _valkey_with(subs: dict):
    valkey_client = create_autospec(redis.Redis, instance=True)
    valkey_client.hgetall.return_value = {
        k.encode(): json.dumps(v).encode() for k, v in subs.items()
    }
    return valkey_client


def test_restore_keeps_credentials_and_queue():
    creds = {"type": "bearer", "token": "secret"}
    valkey_client = _valkey_with({
        "sub-1": {"id": "sub-1", "topic": "cache/a/wis2/x/data/#", "save_path": "x",
                  "filter": {}, "credentials": creds, "queue": "large_files"},
    })
    subscriber = create_autospec(Subscriber, instance=True)

    load_persisted_subscriptions(valkey_client, subscriber)

    topic, subscriptions = subscriber.subscribe.call_args.args
    assert topic == "cache/a/wis2/x/data/#"
    assert subscriptions["sub-1"]["credentials"] == creds
    assert subscriptions["sub-1"]["queue"] == "large_files"


def test_restore_defaults_when_credentials_and_queue_missing():
    valkey_client = _valkey_with({
        "sub-1": {"id": "sub-1", "topic": "t", "save_path": "x", "filter": {}},
    })
    subscriber = create_autospec(Subscriber, instance=True)

    load_persisted_subscriptions(valkey_client, subscriber)

    _, subscriptions = subscriber.subscribe.call_args.args
    assert subscriptions["sub-1"]["credentials"] is None
    assert subscriptions["sub-1"]["queue"] == DEFAULT_QUEUE
