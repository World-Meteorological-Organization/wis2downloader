import os
import subprocess
import sys

from cryptography.fernet import Fernet


def _import_app(**env):
    base = {k: v for k, v in os.environ.items() if k != "SUBSCRIPTIONS_ENCRYPTION_KEY"}
    base.update(VALKEY_PASSWORD="unit_test_password", FLASK_SECRET_KEY="unit_test_secret", **env)
    return subprocess.run([sys.executable, "-c", "import subscription_manager.app"],
                          env=base, capture_output=True, text=True)


def test_missing_key_fails():
    result = _import_app()

    assert result.returncode != 0
    assert "SUBSCRIPTIONS_ENCRYPTION_KEY must be set" in result.stderr


def test_invalid_key_fails_without_echoing_key():
    result = _import_app(SUBSCRIPTIONS_ENCRYPTION_KEY="not-a-valid-key-value")

    assert result.returncode != 0
    assert "SUBSCRIPTIONS_ENCRYPTION_KEY is not a valid key" in result.stderr
    assert "not-a-valid-key-value" not in result.stderr


def test_valid_key_starts():
    result = _import_app(SUBSCRIPTIONS_ENCRYPTION_KEY=Fernet.generate_key().decode())

    assert result.returncode == 0, result.stderr
