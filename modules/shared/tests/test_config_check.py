import pytest

from shared.config_check import Setting, check_settings, require_settings

SETTINGS = (
    Setting('T_PASSWORD', required=True, secret=True),
    Setting('T_PORT', integer=True),
    Setting('T_MODE', validate=lambda v: None if v in ('a', 'b') else "must be 'a' or 'b'"),
)


def test_all_errors_reported_together(monkeypatch):
    monkeypatch.delenv('T_PASSWORD', raising=False)
    monkeypatch.setenv('T_PORT', 'eighty')
    monkeypatch.setenv('T_MODE', 'c')

    errors = check_settings(SETTINGS)

    assert len(errors) == 3
    assert any('T_PASSWORD must be set' in e for e in errors)
    assert any("T_PORT must be an integer, got 'eighty'" in e for e in errors)
    assert any("T_MODE must be 'a' or 'b'" in e for e in errors)


def test_valid_settings(monkeypatch):
    monkeypatch.setenv('T_PASSWORD', 'x')
    monkeypatch.setenv('T_PORT', '80')
    monkeypatch.setenv('T_MODE', 'a')

    assert check_settings(SETTINGS) == []


def test_optional_settings_may_be_unset(monkeypatch):
    monkeypatch.setenv('T_PASSWORD', 'x')
    monkeypatch.delenv('T_PORT', raising=False)
    monkeypatch.delenv('T_MODE', raising=False)

    assert check_settings(SETTINGS) == []


def test_secret_value_never_in_message(monkeypatch):
    monkeypatch.setenv('T_SECRET_INT', 'hunter2')

    errors = check_settings((Setting('T_SECRET_INT', integer=True, secret=True),))

    assert errors and 'hunter2' not in errors[0]


def test_require_settings_exits(monkeypatch):
    monkeypatch.delenv('T_PASSWORD', raising=False)

    with pytest.raises(SystemExit, match='svc: invalid configuration'):
        require_settings('svc', SETTINGS)
