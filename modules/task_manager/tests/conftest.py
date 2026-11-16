import os
from unittest.mock import create_autospec

import pytest
import redis

# shared.valkey_client refuses to import without a password; no connection is
# made until get_valkey_client() is called.
os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")


@pytest.fixture
def request_mock(monkeypatch, tmp_path):
    """Stub Valkey with a dict and the HTTP pool with a mock that fails the download."""
    from task_manager.tasks import wis2

    store: dict[str, dict[bytes, bytes]] = {}
    client = create_autospec(redis.Redis, instance=True)

    def hset(key, field=None, value=None, mapping=None):
        items = mapping or {field: value}
        store.setdefault(key, {}).update({k.encode(): str(v).encode() for k, v in items.items()})
    client.hset.side_effect = hset
    client.hget.side_effect = lambda key, field: store.get(key, {}).get(field.encode())
    client.hexists.side_effect = lambda key, field: field.encode() in store.get(key, {})
    client.set.return_value = True

    monkeypatch.setattr(wis2, "get_valkey_client", lambda: client)
    monkeypatch.setattr(wis2, "incr_counter", lambda *a, **k: None)
    monkeypatch.setattr(wis2, "CONTAINER_DATA_PATH", str(tmp_path))
    request = create_autospec(wis2._pool.request, side_effect=OSError("stop"))
    monkeypatch.setattr(wis2._pool, "request", request)
    return request
