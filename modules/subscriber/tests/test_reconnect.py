import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")

from subscriber.subscriber import Subscriber  # noqa: E402

TOPICS = ["cache/a/wis2/+/data/core/weather/#", "cache/a/wis2/x/data/core/obs"]


def _subscriber(topics):
    # Bypass __init__, which connects to the broker
    sub = Subscriber.__new__(Subscriber)
    sub.host = "gb.example"
    sub.active_subscriptions = {t: {"pattern": t, "subscriptions": {}} for t in topics}
    return sub


def test_reconnect_without_session_resubscribes_all_topics():
    client = MagicMock()

    _subscriber(TOPICS)._on_connect(client, None, SimpleNamespace(session_present=False),
                                    ReasonCode(PacketTypes.CONNACK, "Success"), None)

    assert sorted(c.args[0] for c in client.subscribe.call_args_list) == sorted(TOPICS)


def test_reconnect_with_session_still_resubscribes():
    client = MagicMock()

    _subscriber(TOPICS[:1])._on_connect(client, None, SimpleNamespace(session_present=True),
                                        ReasonCode(PacketTypes.CONNACK, "Success"), None)

    client.subscribe.assert_called_once_with(TOPICS[0], qos=0)


def test_failed_connect_does_not_subscribe():
    client = MagicMock()

    _subscriber(TOPICS)._on_connect(client, None, SimpleNamespace(session_present=False),
                                    ReasonCode(PacketTypes.CONNACK, "Not authorized"), None)

    client.subscribe.assert_not_called()
