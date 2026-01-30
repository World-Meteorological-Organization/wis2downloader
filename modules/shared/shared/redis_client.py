"""Redis client"""
from functools import lru_cache
import os
from typing import List, Optional, Tuple

import redis

from .logging import setup_logging

LOGGER = setup_logging(__name__)

REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB: int = int(os.getenv("REDIS_DATABASE", 0))

_redis_client: Optional[redis.Redis] = None


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """Initialize and return the Redis client."""
    global _redis_client
    if _redis_client is None:
        LOGGER.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            _redis_client.ping()
            LOGGER.info("Successfully connected to Redis")
        except Exception as e:
            LOGGER.error(f"Error connecting to Redis: {e}")
            raise ConnectionError(f"Could not connect to Redis: {e}")
    return _redis_client