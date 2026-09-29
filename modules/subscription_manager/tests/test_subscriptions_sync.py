import json
import os
from unittest.mock import create_autospec

import pytest
import redis
from cryptography.fernet import Fernet

os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")
os.environ.setdefault("FLASK_SECRET_KEY", "unit_test_secret")
os.environ.setdefault("SUBSCRIPTIONS_ENCRYPTION_KEY", Fernet.generate_key().decode())

from subscription_manager import app as app_module  # noqa: E402
from subscription_manager.subscriptions_file import read_subscriptions, write_subscriptions  # noqa: E402

CREDS = {"type": "bearer", "token": "secret"}
SUB = {"id": "sub-1", "topic": "t1", "save_path": "a", "filter": {}, "credentials": CREDS, "queue": "large_files"}


@pytest.fixture
def valkey_client(monkeypatch):
    client = create_autospec(redis.Redis, instance=True)
    client.hgetall.return_value = {}
    monkeypatch.setattr(app_module, "get_valkey_client", lambda: client)
    return client


@pytest.fixture
def subs_file(tmp_path, monkeypatch):
    path = tmp_path / "subscriptions.json"
    monkeypatch.setattr(app_module, "SUBSCRIPTIONS_FILE", path)
    return path


@pytest.fixture
def published(monkeypatch):
    commands = []
    monkeypatch.setattr(app_module, "publish_command", lambda c: commands.append(c) or True)
    return commands


def _valkey_holds(valkey_client, subs: dict):
    valkey_client.hgetall.return_value = {k.encode(): json.dumps(v).encode() for k, v in subs.items()}


def test_persist_saves_file(valkey_client, subs_file):
    _valkey_holds(valkey_client, {"sub-1": SUB})

    assert app_module._persist_subscription("sub-1", SUB)

    assert read_subscriptions(subs_file, app_module.FERNET) == {"sub-1": SUB}


def test_delete_saves_file(valkey_client, subs_file):
    write_subscriptions(subs_file, {"sub-1": SUB}, app_module.FERNET)
    _valkey_holds(valkey_client, {})

    assert app_module._delete_subscription("sub-1")

    assert read_subscriptions(subs_file, app_module.FERNET) == {}


def test_save_failure_does_not_fail_persist(valkey_client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "SUBSCRIPTIONS_FILE", tmp_path / "missing" / "subscriptions.json")

    assert app_module._persist_subscription("sub-1", SUB)


def test_sync_restores_when_valkey_empty(valkey_client, subs_file, published):
    write_subscriptions(subs_file, {"sub-1": SUB}, app_module.FERNET)
    before = subs_file.read_text()

    app_module.sync_subscriptions_file()

    mapping = valkey_client.hset.call_args.kwargs["mapping"]
    assert json.loads(mapping["sub-1"]) == SUB
    assert published == [{
        "action": "subscribe", "topic": "t1",
        "subscriptions": {"sub-1": {"id": "sub-1", "save_path": "a", "filter": {},
                                    "credentials": CREDS, "queue": "large_files"}},
    }]
    assert subs_file.read_text() == before


def test_sync_saves_when_valkey_has_subscriptions(valkey_client, subs_file, published):
    _valkey_holds(valkey_client, {"sub-1": SUB})

    app_module.sync_subscriptions_file()

    assert read_subscriptions(subs_file, app_module.FERNET) == {"sub-1": SUB}
    valkey_client.hset.assert_not_called()
    assert published == []


def test_sync_does_nothing_without_file_or_subscriptions(valkey_client, subs_file, published):
    app_module.sync_subscriptions_file()

    assert not subs_file.exists()
    assert published == []
