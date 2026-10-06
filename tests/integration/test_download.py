"""
End-to-end download flow test.

Requires TEST_FILE_URL to be set to a small publicly accessible file URL.
The file must be served over plain HTTP or HTTPS and have a MIME type in the
default allowed list (text/plain, application/octet-stream, etc.).

Set the following environment variables before running:
  TEST_FILE_URL      - URL of the test file to download (required)
  API_BASE_URL       - Flask API base URL (default: http://localhost:5001)
  MQTT_HOST          - Mosquitto host (default: localhost)
  MQTT_PORT          - Mosquitto port (default: 1883)
  VALKEY_TEST_HOST    - Valkey host reachable from the test runner (default: localhost)
  VALKEY_TEST_PORT    - Valkey port (default: 6379)
  VALKEY_PASSWORD     - Valkey password (default: ci_test_password)
"""
import json
import os
import time
import uuid

import paho.mqtt.publish as mqtt_publish
import pytest
import redis
import requests
from pywis_pubsub.wnm.publish import create_message, get_url_info

TEST_FILE_URL = os.getenv("TEST_FILE_URL", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5001")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
VALKEY_TEST_HOST = os.getenv("VALKEY_TEST_HOST", "localhost")
VALKEY_TEST_PORT = int(os.getenv("VALKEY_TEST_PORT", "6379"))
VALKEY_PASSWORD = os.getenv("VALKEY_PASSWORD", "ci_test_password")

TEST_TOPIC = "origin/a/wis2/test-centre/data/core/test"
TRACKER_PREFIX = "wis2:notifications:data:tracker:by-msg-id"
POLL_INTERVAL_S = 2
POLL_TIMEOUT_S = 120


@pytest.fixture(scope="module")
def valkey_client():
    r = redis.Redis(
        host=VALKEY_TEST_HOST,
        port=VALKEY_TEST_PORT,
        password=VALKEY_PASSWORD,
        socket_connect_timeout=5,
    )
    r.ping()
    return r


def _poll_tracker(valkey_client, msg_id: str, timeout: int = POLL_TIMEOUT_S) -> str:
    """Poll the Valkey tracker until status is set, then return it."""
    key = f"{TRACKER_PREFIX}:{msg_id}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = valkey_client.hget(key, "status")
        if raw is not None:
            return raw.decode()
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(
        f"Tracker key '{key}' not set within {timeout}s. "
        "Check celery-workers-small-files logs."
    )


def _make_notification(msg_id: str, data_id: str) -> dict:
    url_info = get_url_info(TEST_FILE_URL)
    msg = create_message(
        topic=TEST_TOPIC,
        content_type=None,
        url_info=url_info,
        identifier=msg_id,
        geometry=[],
        datetime_=None,
    )
    msg['properties']['data_id'] = data_id
    return msg


@pytest.mark.skipif(not TEST_FILE_URL, reason="TEST_FILE_URL not set")
class TestDownloadFlow:

    @pytest.fixture(autouse=True)
    def subscription(self, valkey_client):
        """Create a subscription for the test topic, remove it after the test."""
        # Clear tracker and lock keys so tests don't share dedup state.
        # Tests use the same file URL (same hash), so without this the second
        # test's first delivery would be deduplicated against the first test's result.
        for pattern in (b"wis2:notifications:data:tracker:*", b"wis2:notification:data:lock:*"):
            keys = valkey_client.keys(pattern)
            if keys:
                valkey_client.delete(*keys)

        # The subscriber's CommandListener polls at 1-second intervals, so any
        # commands queued by earlier steps (e.g. API integration tests) must be
        # fully processed before we subscribe. Allow 15 s for up to ~15 pending
        # commands to drain, so the MQTT SUBSCRIBE is confirmed before we publish
        # and QoS-0 messages aren't silently dropped.
        time.sleep(15)

        unique_target = f"test_run_{uuid.uuid4().hex[:8]}"
        r = requests.post(
            f"{API_BASE_URL}/subscriptions",
            json={"topic": TEST_TOPIC, "target": unique_target},
        )
        assert r.status_code == 201, f"Failed to create subscription: {r.text}"
        sub = r.json()

        # Give the subscriber's CommandListener time to process the Valkey
        # pub/sub event and issue the MQTT SUBSCRIBE to Mosquitto.
        # QoS 0 drops messages published before the subscription is confirmed,
        # so we need to wait long enough even in a slow CI environment.
        time.sleep(10)

        yield sub

        requests.delete(f"{API_BASE_URL}/subscriptions/{sub['id']}")

    def test_notification_triggers_successful_download(self, valkey_client, subscription):
        msg_id = str(uuid.uuid4())
        data_id = str(uuid.uuid4())

        notification = _make_notification(msg_id, data_id)

        # Publish the WIS2 notification to the local Mosquitto broker.
        mqtt_publish.single(
            topic=TEST_TOPIC,
            payload=json.dumps(notification),
            hostname=MQTT_HOST,
            port=MQTT_PORT,
            qos=0,
        )
        time.sleep(POLL_INTERVAL_S * 3)
        status = _poll_tracker(valkey_client, msg_id)
        assert status == "SUCCESS", (
            f"Expected download status SUCCESS, got '{status}'. "
            f"Check celery-workers-small-files logs for msg_id={msg_id}."
        )

    def test_duplicate_notification_is_skipped(self, valkey_client, subscription):
        """Publishing the same message ID twice must result in SKIPPED on the second delivery."""
        msg_id = str(uuid.uuid4())
        data_id = str(uuid.uuid4())
        notification = _make_notification(msg_id, data_id)

        payload = json.dumps(notification)

        # First publish — expect SUCCESS.
        mqtt_publish.single(
            topic=TEST_TOPIC, payload=payload,
            hostname=MQTT_HOST, port=MQTT_PORT, qos=0,
        )
        first_status = _poll_tracker(valkey_client, msg_id)
        assert first_status == "SUCCESS", f"First download got '{first_status}'"

        msg_id = str(uuid.uuid4())
        data_id = str(uuid.uuid4())
        notification = _make_notification(msg_id, data_id)

        payload = json.dumps(notification)
        # Second publish with the same msg_id — must be deduplicated.
        mqtt_publish.single(
            topic=TEST_TOPIC, payload=payload,
            hostname=MQTT_HOST, port=MQTT_PORT, qos=0,
        )
        # Allow time for the second task to be processed.
        time.sleep(POLL_INTERVAL_S * 3)
        second_status = _poll_tracker(valkey_client, msg_id)
        assert second_status in ("SKIPPED"), (
            f"Second delivery got unexpected status '{second_status}'"
        )
