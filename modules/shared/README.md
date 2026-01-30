# Shared Module

Common utilities used across all WIS2 Downloader services.

## Overview

This module provides:
- Redis client singleton with automatic reconnection
- Centralized logging configuration with UTC timestamps

## Documentation

- [Developer Guide](../../docs/developer-guide.adoc) - Architecture and code details

## Usage

```python
from shared import get_redis_client, setup_logging

# Configure root logger (call once at startup)
setup_logging()

# Get module-specific logger
LOGGER = setup_logging(__name__)

# Get Redis client (singleton)
redis = get_redis_client()
redis.set('key', 'value')
```

## Key Files

| File | Description |
|------|-------------|
| `redis_client.py` | Redis client singleton |
| `logging.py` | Centralized logging with UTC timestamps |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DATABASE` | `0` | Redis database number |
| `LOG_LEVEL` | `DEBUG` | Logging level |
