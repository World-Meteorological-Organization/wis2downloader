# Task Manager Module

Celery tasks for downloading and processing WIS2 data.

## Overview

This module provides:
- Celery worker configuration with Redis backend
- Download tasks with deduplication, filtering, and hash verification
- Prometheus metrics for monitoring
- Workflow chains for task orchestration

## Documentation

- [Developer Guide](../../docs/developer-guide.adoc) - Architecture and code details
- [Admin Guide](../../docs/admin-guide.adoc) - Configuration and monitoring

## Entry Points

- `task_manager_start` - CLI entry point for starting Celery worker

## Key Files

| File | Description |
|------|-------------|
| `worker.py` | Celery app configuration |
| `tasks/wis2.py` | Download and processing tasks |
| `workflows/__init__.py` | Task chain definitions |

## Tasks

### `download_from_wis2`

Downloads a file from WIS2 notification.

Features:
- Deduplication via message ID, data ID, and file hash
- Distributed locking to prevent concurrent downloads
- Media type filtering
- Hash verification
- Automatic file organization by date

### `decode_and_ingest`

Placeholder for post-download processing (decoding BUFR/GRIB, ingestion).
