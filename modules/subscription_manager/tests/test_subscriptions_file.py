import json
import os
import stat

import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")

from subscription_manager.subscriptions_file import read_subscriptions, write_subscriptions  # noqa: E402

CREDS = {"type": "basic", "username": "user", "password": "hunter2"}
SUBS = {
    "sub-1": {"id": "sub-1", "topic": "t1", "save_path": "a", "filter": {}, "credentials": CREDS,
              "queue": "large_files"},
    "sub-2": {"id": "sub-2", "topic": "t2", "save_path": "b", "filter": {}, "credentials": None},
}


@pytest.fixture
def fernet():
    return Fernet(Fernet.generate_key())


def test_round_trip(tmp_path, fernet):
    path = tmp_path / "subscriptions.json"

    write_subscriptions(path, SUBS, fernet)

    assert read_subscriptions(path, fernet) == SUBS


def test_credentials_not_stored_in_plain_text(tmp_path, fernet):
    path = tmp_path / "subscriptions.json"

    write_subscriptions(path, SUBS, fernet)

    text = path.read_text()
    assert "hunter2" not in text
    assert "credentials_encrypted" in json.loads(text)["subscriptions"]["sub-1"]


def test_file_readable_by_owner_only(tmp_path, fernet):
    path = tmp_path / "subscriptions.json"

    write_subscriptions(path, SUBS, fernet)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in tmp_path.iterdir()] == ["subscriptions.json"]


def test_wrong_key_restores_without_credentials(tmp_path, fernet):
    path = tmp_path / "subscriptions.json"
    write_subscriptions(path, SUBS, fernet)

    restored = read_subscriptions(path, Fernet(Fernet.generate_key()))

    assert restored["sub-1"]["credentials"] is None
    assert restored["sub-1"]["topic"] == "t1"


def test_unsupported_version_rejected(tmp_path, fernet):
    path = tmp_path / "subscriptions.json"
    path.write_text(json.dumps({"version": 99, "subscriptions": {}}))

    with pytest.raises(ValueError):
        read_subscriptions(path, fernet)
