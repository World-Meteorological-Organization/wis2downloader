import os

from cryptography.fernet import Fernet

os.environ.setdefault("VALKEY_PASSWORD", "unit_test_password")
os.environ.setdefault("FLASK_SECRET_KEY", "unit_test_secret")
os.environ.setdefault("SUBSCRIPTIONS_ENCRYPTION_KEY", Fernet.generate_key().decode())

from subscription_manager.app import _redact_command  # noqa: E402

CREDS = {"type": "basic", "username": "user", "password": "hunter2"}


def test_redacts_top_level_credentials():
    command = {"action": "add_subscription", "topic": "t", "sub_id": "1", "credentials": CREDS}

    safe = _redact_command(command)

    assert "hunter2" not in str(safe)
    assert safe["credentials"] == {"type": "basic", "username": "user"}
    assert command["credentials"] == CREDS


def test_redacts_nested_subscription_credentials():
    command = {"action": "subscribe", "topic": "t",
               "subscriptions": {"1": {"id": "1", "credentials": CREDS}}}

    safe = _redact_command(command)

    assert "hunter2" not in str(safe)
    assert command["subscriptions"]["1"]["credentials"] == CREDS


def test_command_without_credentials_unchanged():
    command = {"action": "unsubscribe", "topic": "t"}

    assert _redact_command(command) == command
