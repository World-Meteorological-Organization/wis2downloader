import os
import pytest
import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5001")

TOPIC = "cache/a/wis2/+/+/data/recommended/#"


def test_health_is_healthy():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_list_subscriptions_returns_dict():
    r = requests.get(f"{BASE_URL}/subscriptions")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_create_subscription_missing_topic_returns_400():
    r = requests.post(f"{BASE_URL}/subscriptions", json={})
    assert r.status_code == 400


class TestSubscriptionCRUD:
    """Full create → read → update → delete lifecycle."""

    @pytest.fixture(autouse=True)
    def subscription(self):
        r = requests.post(f"{BASE_URL}/subscriptions", json={"topic": TOPIC, "target": ""})
        assert r.status_code == 201, f"Setup failed: {r.text}"
        data = r.json()
        yield data
        # Cleanup — ignore 404 if already deleted by the test itself
        requests.delete(f"{BASE_URL}/subscriptions/{data['id']}")

    def test_create_returns_location_header(self, subscription):
        assert "Location" in requests.post(
            f"{BASE_URL}/subscriptions", json={"topic": TOPIC + "/other", "target": ""}
        ).headers
        # cleanup the extra one
        r = requests.get(f"{BASE_URL}/subscriptions")
        for sub_id, details in r.json().get(TOPIC + "/other", {}).items():
            requests.delete(f"{BASE_URL}/subscriptions/{sub_id}")

    def test_create_returns_correct_topic(self, subscription):
        assert subscription["topic"] == TOPIC

    def test_get_subscription_by_id(self, subscription):
        r = requests.get(f"{BASE_URL}/subscriptions/{subscription['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == subscription["id"]

    def test_get_unknown_id_returns_404(self):
        r = requests.get(f"{BASE_URL}/subscriptions/does-not-exist")
        assert r.status_code == 404

    def test_list_includes_created_subscription(self, subscription):
        r = requests.get(f"{BASE_URL}/subscriptions")
        assert r.status_code == 200
        assert TOPIC in r.json()

    def test_update_filter(self, subscription):
        new_filter = {"bbox": [-180, -90, 180, 90]}
        r = requests.put(
            f"{BASE_URL}/subscriptions/{subscription['id']}",
            json={"filter": new_filter},
        )
        assert r.status_code == 200
        assert r.json()["filter"]["bbox"] == new_filter["bbox"]

    def test_update_unknown_id_returns_404(self):
        r = requests.put(f"{BASE_URL}/subscriptions/does-not-exist", json={"target": ""})
        assert r.status_code == 404

    def test_delete_subscription(self, subscription):
        r = requests.delete(f"{BASE_URL}/subscriptions/{subscription['id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

        # Confirm it is gone
        r = requests.get(f"{BASE_URL}/subscriptions/{subscription['id']}")
        assert r.status_code == 404

    def test_delete_unknown_id_returns_404(self):
        r = requests.delete(f"{BASE_URL}/subscriptions/does-not-exist")
        assert r.status_code == 404


def test_metrics_endpoint_returns_prometheus_text():
    r = requests.get(f"{BASE_URL}/metrics")
    assert r.status_code == 200
    assert "celery_queue_length" in r.text


def test_openapi_spec_is_returned():
    r = requests.get(f"{BASE_URL}/openapi")
    assert r.status_code == 200
