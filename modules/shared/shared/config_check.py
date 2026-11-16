"""Startup configuration check: validate every setting, report all problems, then exit."""
from dataclasses import dataclass
import os
from typing import Callable

from .logging import setup_logging

LOGGER = setup_logging(__name__)


@dataclass(frozen=True)
class Setting:
    name: str
    required: bool = False
    integer: bool = False
    secret: bool = False  # never include the value in messages
    validate: Callable[[str], str | None] | None = None  # returns an error message or None


VALKEY_SETTINGS = (
    Setting('VALKEY_PASSWORD', required=True, secret=True),
    Setting('VALKEY_PORT', integer=True),
    Setting('VALKEY_DATABASE', integer=True),
)


def check_settings(settings) -> list[str]:
    errors = []
    for s in settings:
        value = os.getenv(s.name)
        if value in (None, ''):
            if s.required:
                errors.append(f"{s.name} must be set, run setup.sh to generate .env")
            continue
        if s.integer:
            try:
                int(value)
            except ValueError:
                errors.append(f"{s.name} must be an integer" + ("" if s.secret else f", got {value!r}"))
                continue
        if s.validate and (message := s.validate(value)):
            errors.append(f"{s.name} {message}")
    return errors


def require_settings(service: str, settings) -> None:
    """Exit with every configuration error listed if any setting is invalid."""
    errors = check_settings(settings)
    if errors:
        for error in errors:
            LOGGER.error(error)
        raise SystemExit(f"{service}: invalid configuration:\n  " + "\n  ".join(errors))
