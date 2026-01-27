from functools import lru_cache
import logging
import os
import redis
from redis.sentinel import Sentinel

LOGGER = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL","DEBUG").upper()
LOGGER.setLevel(LOG_LEVEL)

SENTINEL_HOSTS_STR = os.getenv('REDIS_SENTINEL_HOSTS')
MASTER_NAME = os.getenv('REDIS_PRIMARY_NAME', 'redis-primary')
REDIS_DB = int(os.getenv('REDIS_DATABASE', 0))

# fallback to direct connection if no sentinel hosts are provided
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

SENTINEL_HOSTS = []
if SENTINEL_HOSTS_STR:
    for pair in SENTINEL_HOSTS_STR.split(','):
        host, port = pair.split(':')
        SENTINEL_HOSTS.append((host, int(port)))

_sentinel = None
_redis_client = None

@lru_cache(maxsize=1)
def get_redis_client():
    """
    Initializes and returns the Redis master client via Sentinel.
    Uses lru_cache to ensure the connection is only established once.
    """
    global _sentinel, _redis_client
    if _redis_client is None:
        LOGGER.info(f"Connecting to Redis Sentinel at: {SENTINEL_HOSTS}")
        try:
            if SENTINEL_HOSTS:
                _sentinel = Sentinel(SENTINEL_HOSTS,
                                     socket_timeout=1,
                                     socket_connect_timeout=1,
                                     retry_on_timeout=True)
                _redis_client = _sentinel.master_for(MASTER_NAME, db=REDIS_DB)
                LOGGER.info(f"Connected to Redis Sentinel at: {SENTINEL_HOSTS}")
            else:
                _redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT,
                                            db=REDIS_DB)
                LOGGER.info("Falling back to direct connection to Redis.")
            # Test connection
            _redis_client.ping()
            LOGGER.info("Successfully connected to Redis")

        except Exception as e:
            LOGGER.error(f"Error connecting to Redis: {e}")
            # In a critical failure scenario, raise the error or use a fallback
            raise ConnectionError(f"Could not connect to Redis: {e}")

    return _redis_client