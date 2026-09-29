# Shared Module

Common utilities used across all WIS2 Downloader services.

## Overview

This module provides:
- Valkey client singleton with automatic reconnection
- Centralized logging configuration with UTC timestamps

## Documentation

- [Developer Guide](../../docs/developer-guide.adoc) - Architecture and code details

## Usage

```python
from shared import get_valkey_client, setup_logging

# Configure root logger (call once at startup)
setup_logging()

# Get module-specific logger
LOGGER = setup_logging(__name__)

# Get Valkey client (singleton)
valkey = get_valkey_client()
valkey.set('key', 'value')
```

## Key Files

| File | Description |
|------|-------------|
| `valkey_client.py` | Valkey client singleton |
| `logging.py` | Centralized logging with UTC timestamps |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VALKEY_HOST` | `localhost` | Valkey server hostname |
| `VALKEY_PORT` | `6379` | Valkey server port |
| `VALKEY_DATABASE` | `0` | Valkey database number |
| `VALKEY_PASSWORD` | _required_ | Valkey authentication password |
| `LOG_LEVEL` | `DEBUG` | Logging level |
