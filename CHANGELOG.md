# WIS2 Downloader Refactor - Progress Log

## 2026-02-20

### UI Module: Bug Fixes and Architecture Improvements - COMPLETE

**Bug Fixes:**
- Fixed `show_metadata` failing for records where the CMA GDC omits `channel` fields in links (e.g. Kazakhstan synop record). `show_metadata` now looks up the record directly from `merged_records()` rather than relying on a per-session flat index.
- Fixed `_build_merged_records()` discrepancy detection to also flag records where link sets differ between catalogues.
- Fixed `KeyError: 'datasets'` in `_insert_channel()` when a channel string is a prefix of another (e.g. `cache/a/wis2/centre` and `cache/a/wis2/centre/data/...`). Root cause was overwriting the `children` dict; fixed using `setdefault` for each level independently.
- Fixed catalogue search breaking after `render()` was incorrectly changed to `async def` — synchronous callers in `show_view()` cannot `await` it.
- Fixed confirmation dialog rendering too narrow (292 px). Root cause: `.dialog-confirm` class was on `ui.scroll_area` instead of `ui.card`, and buttons were inside the scroll area.

**Architecture:**
- `merged_records()` and `topic_hierarchy()` are now module-level caches in `data.py`, computed once at the end of `scrape_all()`. Previously `_build_merged_records()` was called on every `merged_records()` invocation.
- Added `get_datasets_for_channel(channel)` — strips trailing `/#`, navigates the topic hierarchy, and recursively collects all datasets from that node and its descendants.
- Removed `state.features` — the module-level `_topic_hierarchy` in `data.py` is now the single source of truth for channel→dataset mapping.
- `AppState` reduced to `selected_topics` only; `features`, `selected_datasets`, and `tree_widget` fields removed.
- Link merging: `_build_merged_records()` unions channel-bearing links from all GDCs onto the primary record, so channel data present in any catalogue is preserved on the merged record.

**New Features:**
- Subscription confirmation dialog: before sending to the subscription manager, a dialog shows the full JSON payload (pretty-printed) with Cancel / Confirm buttons.
- Catalogue dataset filter locks to the selected record and is non-editable when a dataset is selected from search results.
- Custom filters (derived from MQTT link metadata `filters` key) are shown in the right sidebar only when selecting from catalogue search results; hidden in tree view.
- Tree view: single-topic selection enforced via `on_select` (native NiceGUI/Quasar behaviour). Using `on_tick` was rejected as it requires a timer race to reset internal state.
- Tree view: topics sorted alphabetically at every level of the hierarchy.

**Changed Files:**
- `modules/ui/data.py` — added `_merged_records`, `_topic_hierarchy`, `_insert_channel()`, `_collect_datasets()`, `_build_topic_hierarchy()`, `get_datasets_for_channel()`, `topic_hierarchy()`; `scrape_all()` rebuilds both caches on completion
- `modules/ui/views/tree.py` — replaced `put_in_dicc` tree-builder with `_to_tree_nodes()`; switched to `on_select`; alphabetical sorting
- `modules/ui/views/catalogue.py` — removed `state.features` population; pass `dataset_id` to `on_topics_picked`; reverted `render` to `def`
- `modules/ui/views/shared.py` — removed `state.features` from `clean_page`; `on_topics_picked` accepts `dataset_id` param; `show_metadata` looks up from `merged_records()`; added `confirm_subscribe()` dialog
- `modules/ui/main.py` — `AppState` reduced to `selected_topics`
- `modules/ui/assets/base.css` — added `.dialog-scroll` and `.dialog-confirm` sizing rules

---

## 2026-02-02

### Phase 8: Security Hardening - COMPLETE

**Fixed Critical/High Issues:**
- Path traversal in downloaded filename - Added directory traversal check in `wis2.py:379-384`
- MQTT TLS certificate not validated - Using `certifi.where()` in `subscriber.py`
- Redis has no password protection - Added `--requirepass` and `REDIS_PASSWORD` required for all clients
- Flask debug mode enabled in production - Controlled by `FLASK_DEBUG` env var, default false
- Weak default Flask secret key - `FLASK_SECRET_KEY` now required, application fails if missing
- Dynamic hash algorithm selection - Whitelist `ALLOWED_HASH_METHODS` (SHA-256/384/512, SHA3 variants)
- Celery serialization not restricted - JSON-only serialization in `worker.py`
- Exception details exposed - Generic error messages, details logged server-side only

**Security Features Added:**
- Hash algorithm whitelist prevents arbitrary algorithm injection
- Path boundary checks prevent directory traversal attacks
- MQTT TLS validation via certifi CA bundle
- Redis authentication required for all connections
- Atomic file operations prevent partial/corrupt writes

### Phase 9: Production Readiness - COMPLETE

**Fixed Issues:**
- Missing graceful shutdown signal handlers - Added SIGTERM/SIGINT handlers in `manager.py`
- GLOBAL_BROKER_HOST not validated - Application exits with code 1 if not set
- Unsafe nested dictionary access - Using `.get()` chains throughout `wis2.py`
- CONTAINER_DATA_PATH/DATA inconsistency - Standardized on `CONTAINER_DATA_PATH`
- CACHE_EXCLUDE_LIST parsing bug - Fixed with list comprehension
- No Celery result expiration - Added `result_expires = 86400`
- TOCTOU race condition in file write - Atomic temp file + rename pattern
- Missing Docker healthchecks - Added healthchecks for all services in `docker-compose.yaml`
- Subscriber not resubscribing on restart - Added `load_persisted_subscriptions()` in `manager.py`
- Unvalidated environment variable type conversions - Added try/except validation

**Changes:**
- `modules/shared/shared/redis_client.py` - REDIS_PASSWORD now required, fails on startup if missing
- `modules/subscription_manager/subscription_manager/app.py` - FLASK_SECRET_KEY required
- `modules/task_manager/task_manager/worker.py` - JSON-only serialization, result expiration
- `modules/task_manager/task_manager/tasks/wis2.py` - Path traversal checks, hash whitelist, atomic writes
- `modules/subscriber/subscriber/manager.py` - Signal handlers, subscription reload
- `docker-compose.yaml` - Redis password, healthchecks for all services

---

## 2026-01-30

### Infrastructure Simplification - Single Redis Instance

**Removed:**
- Redis Sentinel cluster (3 sentinels)
- Redis replicas (2 replicas)
- Static IP network configuration (172.28.0.0/16)
- Sentinel-specific environment variables (`REDIS_SENTINEL_HOSTS`, `REDIS_PRIMARY_NAME`)
- Celery transport options (`CELERY_BROKER_TRANSPORT_OPTIONS`, `CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS`)
- `/containers/redis-sentinel/` directory

**Changed:**
- `docker-compose.yaml` - Single Redis instance, simplified network
- `default.env` - Direct Redis connection variables
- `modules/shared/shared/redis_client.py` - Removed Sentinel support, direct connection only
- `modules/task_manager/task_manager/worker.py` - Direct Redis URLs
- All documentation updated to reflect single Redis architecture

**Rationale:**
Sentinel was over-engineered for most deployment scenarios. Single Redis provides:
- Simpler configuration and debugging
- Reduced resource usage (5 fewer containers)
- Faster startup time
- Easier local development

---

## 2026-01-27

### Phase 1: Subscriber/Subscription-Manager Separation - COMPLETE

**Problem:** Refactor was left incomplete 2 months ago. Services wouldn't start due to missing imports and undefined variables.

**Fixed:**
- `modules/subscriber/setup.py` - Created with entry point `subscriber_start`
- `modules/subscriber/subscriber/__init__.py` - Added exports
- `modules/subscriber/subscriber/manager.py` - Added `from uuid import uuid4`
- `modules/subscriber/subscriber/command_listener.py` - Added `import os`, uses shared Redis client
- `modules/subscription_manager/subscription_manager/__init__.py` - Removed broken subscriber imports
- `modules/subscription_manager/subscription_manager/app.py` - Fixed delete endpoint, added COMMAND_CHANNEL
- `containers/subscriber/Dockerfile` - Created new Dockerfile for subscriber service
- `docker-compose.yaml` - Updated subscriber-france to use new Dockerfile

### Phase 2: Redis HA Improvements - COMPLETE

**Problem:** Duplicated Redis client code across modules, no single Redis fallback.

**Fixed:**
- `modules/shared/` - Created shared module with `redis_client.py`
- `modules/shared/shared/redis_client.py` - Centralized Redis client with Sentinel support and single Redis fallback
- Updated all modules to import from shared
- Updated all Dockerfiles to install shared module

### Redis Sentinel Failover - COMPLETE

**Problem:** Sentinel failover not working in Docker Compose due to hostname resolution issues causing repeated tilt mode.

**Root Cause:** When a container stops, Docker DNS removes its hostname. Sentinel's `resolve-hostnames yes` caused constant resolution failures and tilt mode re-entry, blocking failover.

**Solution:** Implemented static IPs for all Redis components.

**Changes:**
- `docker-compose.yaml` - Added `redis-net` network with subnet 172.28.0.0/16
  - redis-primary: 172.28.0.10
  - redis-replica-1: 172.28.0.11
  - redis-replica-2: 172.28.0.12
  - redis-sentinel-1: 172.28.0.20
  - redis-sentinel-2: 172.28.0.21
  - redis-sentinel-3: 172.28.0.22
- `containers/redis-sentinel/sentinel.conf` - Uses static IP instead of hostname:
  ```
  sentinel monitor redis-primary 172.28.0.10 6379 2
  sentinel down-after-milliseconds redis-primary 5000
  sentinel failover-timeout redis-primary 60000
  protected-mode no
  ```

**Result:** Failover completes in ~2 seconds.

### Subscriber Reconnection Fix - COMPLETE

**Problem:** After Redis failover, subscriber's command_listener didn't reconnect properly.

**Root Cause:** `pubsub` object created once in `__init__`, connection error handler just slept and continued without recreating pubsub or resubscribing.

**Fix:** Added `_reconnect()` method to `command_listener.py`:
```python
def _reconnect(self):
    """Recreate pubsub and resubscribe after connection failure."""
    try:
        self.pubsub.close()
    except Exception:
        pass
    self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
    self.pubsub.subscribe(self.channel)
    LOGGER.info(f"Reconnected and resubscribed to channel: {self.channel}")
```

**Result:** Subscriber auto-reconnects after failover.

---

## 2026-01-28

### Phase 3: Configuration Improvements - COMPLETE

**Fixed:**
- Subscription storage uses Redis only (removed SQLite)
- Cache blacklist made configurable via CACHE_BLACKLIST env var
- Celery worker configuration improved with proper JSON parsing
- Fixed broker/backend transport options JSON defaults

### Phase 4: Download Task Improvements - COMPLETE

**Fixed:**
- Improved file type detection
- Added STATUS_QUEUED constant
- Added centre_id extraction to result dict
- Added dataset field to result
- Added media-type filtering via subscription filters

**Media-type Filtering:**
- Subscriptions can now include `filters.media_types` (list of allowed types)
- Filter is applied early in workflow, before download
- Uses fnmatch for wildcard support (e.g., `application/x-grib*`)

### Phase 5: Metrics Improvements - COMPLETE

**Fixed:**
- All metrics renamed with `wis2_` prefix for consistency:
  - `wis2_notifications_received`
  - `wis2_notifications_skipped`
  - `wis2_downloads_failed`
  - `wis2_downloads_total`
  - `wis2_downloads_bytes_total`
  - `wis2_celery_queue_length`
- Fixed Prometheus multiprocess mode initialization
- Added `multiprocess_mode='livesum'` to Gauge metrics
- Fixed shared volume between celery and subscription-manager containers
- Added Grafana service with auto-provisioned Prometheus/Loki datasources

**Multiprocess Mode Fix:**
- subscription-manager clears `/tmp/prometheus_metrics/` on startup
- celery depends_on subscription-manager for proper startup order
- Both containers share prometheus-metrics-data volume

### Phase 6: Code Quality - COMPLETE

**Fixed:**
- Created centralized logging in `modules/shared/shared/logging.py`
- All modules updated to use `setup_logging()` from shared
- Removed unused imports across all modules
- Removed commented/dead code
- Fixed credential logging security issue (was logging passwords)
- Changed verbose log messages from WARNING to DEBUG

### Phase 7: Documentation - COMPLETE

**Added:**
- Main project `README.adoc` with architecture overview
- `docs/admin-guide.adoc` - Deployment, configuration, monitoring
- `docs/user-guide.adoc` - Subscriptions, filtering, common use cases
- `docs/api-reference.adoc` - REST API documentation
- `docs/developer-guide.adoc` - Architecture, modules, extending
- Module READMEs for shared, subscriber, subscription_manager, task_manager
- Apache 2.0 license to all modules and main repo

**Updated:**
- `openapi.yml` - Complete rewrite with filters, correct schemas, examples
- Wildcard support for media type filtering (fnmatch)
- Fixed WIS2 topic examples (correct centre-id format with ISO2C prefix)

**Cleaned up:**
- Removed duplicate `config/redis-sentinel/sentinel.conf`
- Fixed sentinel.conf permissions
- Fixed CRLF line endings
