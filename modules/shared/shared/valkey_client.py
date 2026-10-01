"""Valkey client"""
from functools import lru_cache
import os
import time
from typing import Optional

import redis

from .logging import setup_logging

LOGGER = setup_logging(__name__)


def _int_env(name: str, default: int) -> int:
    # Invalid values are reported by config_check.require_settings at service startup
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


VALKEY_HOST: str = os.getenv("VALKEY_HOST", "localhost")
VALKEY_PORT: int = _int_env("VALKEY_PORT", 6379)
VALKEY_DB: int = _int_env("VALKEY_DATABASE", 0)
VALKEY_PASSWORD: str | None = os.getenv("VALKEY_PASSWORD")

_valkey_client: Optional[redis.Redis] = None


@lru_cache(maxsize=1)
def get_valkey_client() -> redis.Redis:
    """Initialize and return the Valkey client."""
    global _valkey_client
    if _valkey_client is None:
        LOGGER.info(f"Connecting to Valkey at {VALKEY_HOST}:{VALKEY_PORT}")
        while True:
            try:
                _valkey_client = redis.Redis(
                    host=VALKEY_HOST,
                    port=VALKEY_PORT,
                    db=VALKEY_DB,
                    password=VALKEY_PASSWORD,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                _valkey_client.ping()
                LOGGER.info("Successfully connected to Valkey")
                break
            except redis.exceptions.BusyLoadingError:
                _valkey_client = None
                LOGGER.warning(
                    "Valkey is loading dataset, retrying in 5s..."
                )
                time.sleep(5)
            except Exception as e:
                LOGGER.error(f"Error connecting to Valkey: {e}")
                raise ConnectionError(f"Could not connect to Valkey: {e}")
    return _valkey_client
