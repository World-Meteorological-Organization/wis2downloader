import base64
from celery.exceptions import MaxRetriesExceededError, Retry
from celery.utils.log import get_task_logger
import datetime as dt
from functools import wraps
import importlib
import magic
import mimetypes
import os
from pathlib import Path
import tempfile
import urllib3
from urllib.parse import urlsplit

from task_manager.worker import app as app

# Import shared utilities
from shared import get_redis_client, apply_filters, MatchContext, incr_counter

LOGGER = get_task_logger(__name__)

CONTAINER_DATA_PATH = os.getenv("CONTAINER_DATA_PATH", "/data")  # this needs checking

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_PENDING = "PENDING"
STATUS_VALID_CONDITIONS = [STATUS_SUCCESS, STATUS_FAILED, STATUS_SKIPPED, STATUS_PENDING]
try:
    REDIS_TTL_SECONDS = int(os.getenv("REDIS_TTL_SECONDS", 3600))
    LOCK_EXPIRE = int(os.getenv("REDIS_MESSAGE_LOCK", 300))
except Exception as e:
    LOGGER.error(f"Error getting environment variables {e}")
    raise e
CACHE_EXCLUDE_LIST = [x.strip() for x in os.getenv("GC_EXCLUDE", "").split(",") if x.strip()]

ALLOWED_HASH_METHODS = ("sha256", "sha384", "sha512", "sha3_256",
                        "sha3_384", "sha3_512")

RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})

_pool = urllib3.PoolManager()
hash_module = importlib.import_module("hashlib")


def _build_auth_headers(credentials: dict | None) -> dict:
    if not credentials:
        return {}
    if credentials.get("type") == "basic":
        raw = f"{credentials['username']}:{credentials['password']}"
        encoded = base64.b64encode(raw.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    if credentials.get("type") == "bearer":
        return {"Authorization": f"Bearer {credentials['token']}"}
    return {}

DOWNLOAD_CHUNK_SIZE = int(os.getenv("DOWNLOAD_CHUNK_SIZE", str(64 * 1024)))  # 64 KB per chunk
_PROGRESS_LOG_INTERVAL = 1 * 1024 * 1024  # log a progress line every 50 MB


TRACKER = "wis2:notifications:data:tracker"

mimetypes.add_type('application/bufr', '.bufr')
mimetypes.add_type('application/grib', '.grib')

DEFAULT_ACCEPTED_MEDIA_TYPES = [
    'image/gif', 'image/jpeg', 'image/png', 'image/tiff',
    'application/pdf', 'application/postscript',
    'application/bufr', 'application/grib',
    'application/x-hdf', 'application/x-hdf5', 'application/x-netcdf', 'application/x-netcdf4',
    'text/plain', 'text/html', 'text/xml', 'text/csv', 'text/tab-separated-values',
    'application/octet-stream',
]

DEFAULT_FILTER = {
    "name": "default",
    "rules": [
        {
            "id": "default-media-type",
            "order": 1,
            "match": {"all": [
                {"media_type": {"exists": True}},
                {"media_type": {"not_in": DEFAULT_ACCEPTED_MEDIA_TYPES}},
            ]},
            "action": "reject",
            "reason": "Media type not in default allowed list",
        }
    ]
}


def set_status(key, type, status):
    if key in (None, ''):
        LOGGER.warning("No key provided")
        return
    if type not in ('by-msg-id', 'by-hash', 'by-data-id'):
        LOGGER.warning(f"Invalid type {type}")
        return
    if status not in STATUS_VALID_CONDITIONS:
        LOGGER.warning(f"Invalid status '{status}' for {key} ({type})")
    tracker_id = f"{TRACKER}:{type}:{key}"

    try:
        redis_client = get_redis_client()
        redis_client.hset(tracker_id, 'status', status)
        redis_client.expire(tracker_id, REDIS_TTL_SECONDS)  # Set expiration
    except Exception as e:
        LOGGER.error(f"Redis error in set_status: {e}")


def get_status(key, type):
    status = None
    if key in (None, ''):
        LOGGER.warning("No key provided")
        return status
    if type not in ('by-msg-id', 'by-hash', 'by-data-id'):
        LOGGER.warning(f"Invalid type {type}")
        return status

    tracker_id = f"{TRACKER}:{type}:{key}"

    try:
        redis_client = get_redis_client()
        if redis_client.hexists(tracker_id, 'status'):
            status = redis_client.hget(tracker_id, 'status')
            status = status.decode('utf-8')
            if status not in STATUS_VALID_CONDITIONS:
                LOGGER.warning(f"Invalid status '{status}' for {key}")
    except Exception as e:
        LOGGER.error(f"Redis error in get_status: {e}")

    return status


def guess_file_type(data):
    mime = magic.from_buffer(data, mime=True)
    if mime == 'application/octet-stream':  # we need to manually guess for BUFR, GRIB, etc
        if len(data) >= 4:
            header = data[0:4].decode('utf-8', errors='ignore')
            if header == 'BUFR':
                mime = 'application/bufr'
            elif header == 'GRIB':
                mime = 'application/grib'
    ext = mimetypes.guess_extension(mime)
    return mime, ext


def _stream_response_to_file(
    response,
    dest_path: str,
    hasher,
    download_url: str,
) -> tuple[int, str]:
    """Stream *response* body to *dest_path*.

    Writes DOWNLOAD_CHUNK_SIZE bytes at a time, updating *hasher* (a hashlib
    hash object, or None) incrementally and logging progress every
    _PROGRESS_LOG_INTERVAL bytes.

    Returns (total_bytes_written, detected_mime_type).
    Raises OSError on disk errors or urllib3 exceptions on network errors.
    The caller is responsible for calling response.release_conn().
    """
    actual_size = 0
    last_log_at = 0
    mime_type = "application/octet-stream"
    first_chunk = True

    with open(dest_path, "wb") as fh:
        for chunk in response.stream(DOWNLOAD_CHUNK_SIZE):
            if not chunk:
                continue
            if first_chunk:
                mime_type, _ = guess_file_type(chunk[:8192])
                first_chunk = False
            fh.write(chunk)
            if hasher is not None:
                hasher.update(chunk)
            actual_size += len(chunk)
            if actual_size - last_log_at >= _PROGRESS_LOG_INTERVAL:
                LOGGER.info(
                    "Downloading %s: %.1f MB received",
                    download_url,
                    actual_size / (1024 * 1024),
                )
                last_log_at = actual_size

    if actual_size > 0:
        LOGGER.debug(
            "Download complete: %.1f MB from %s",
            actual_size / (1024 * 1024),
            download_url,
        )
    return actual_size, mime_type


def _apply_job_filter(filter_config: dict, ctx: MatchContext) -> tuple[str, str | None]:
    """Evaluate the filter for a job context.

    Delegates to the rule-based engine when a filter is configured.
    No filter means accept everything.

    Returns ('accept', reason | None) or ('reject', reason).
    """
    return apply_filters(filter_config or DEFAULT_FILTER, ctx)


def _select_download_link(links):
    """
    Prefers 'update' (overwrite=True), otherwise 'canonical' (overwrite=False).
    Returns (download_url, expected_length, overwrite)
    """
    download_url = None
    expected_length = None
    overwrite = False
    for link in links:
        rel = link.get('rel')
        if rel == 'update':
            download_url = link.get('href')
            expected_length = link.get('length')
            overwrite = True
            break
        if rel == 'canonical' and download_url is None:
            download_url = link.get('href')
            expected_length = link.get('length')
    return download_url, expected_length, overwrite


def _now_utc_str() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def metrics_collector(func):
    """Collect metrics for each notification processed.

    Metrics collected:
    - wis2downloader_notifications_total: Count by status (success/failed/skipped)
    - wis2downloader_downloads_total: Successful downloads by cache and media_type
    - wis2downloader_downloads_bytes_total: Bytes downloaded by cache and media_type
    - wis2downloader_skipped_total: Skipped notifications by reason
    - wis2downloader_failed_total: Failed downloads by cache and reason
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        status_code = result.get('status', '')
        global_cache = result.get('global_cache', '') or 'unknown'
        error_class = result.get('error_class', '') or 'unknown'
        file_size = result.get('actual_filesize', 0)
        media_type = result.get('media_type', '') or 'unknown'

        try:
            # Always count the notification by final status
            incr_counter('notifications_total', {'status': status_code.lower()})

            if status_code == STATUS_SKIPPED:
                incr_counter('skipped_total', {'reason': error_class})

            if status_code == STATUS_FAILED:
                incr_counter('failed_total', {'cache': global_cache, 'reason': error_class})

            if status_code == STATUS_SUCCESS:
                incr_counter('downloads_total', {'cache': global_cache, 'media_type': media_type})
                incr_counter('downloads_bytes_total', {'cache': global_cache, 'media_type': media_type}, file_size)
                incr_counter('disk_downloads_bytes', {}, file_size)

        except Exception as e:
            LOGGER.error(f"Error collecting metrics: {e}", exc_info=True)

        return result
    return wrapper


@app.task(bind=True)
@metrics_collector
def download_from_wis2(self, job):
    # set up return dict
    result = {
        'id': None,
        'data_id': None,
        'topic': None,
        'broker': None,
        'global_cache': None,
        'centre_id': None,
        'metadata_id': None,
        'received': None,
        'queued': None,
        'download_start': None,
        'download_end': None,
        'download_url': None,
        'processed': None,
        'status': None,
        'reason': None,
        'error_class': None,
        'filepath': None,
        'media_type': None,
        'save': False,
        'expected_hash': None,
        'actual_hash': None,
        'hash_method': None,
        'valid_hash': None,
        'expected_filesize': None,
        'actual_filesize': None
    }

    # get output directory
    target_directory = job.get("target", "")

    # now get topic
    topic = job.get("topic")
    result['topic'] = topic

    if topic is None:
        result['status'] = STATUS_FAILED
        result['reason'] = "Notification message is missing 'topic'"
        result['error_class'] = "MissingTopicError"
        return result

    # decompose topic to get centre-id
    topic_parts = topic.split('/')
    centre_id = topic_parts[3] if len(topic_parts) > 3 and topic_parts[2] == 'wis2' else 'unknown'
    result['centre_id'] = centre_id

    media_type = 'unknown'
    result['media_type'] = media_type

    # get identifiers (incl. file hash if present)
    message_id = job.get('payload', {}).get('id')
    result['id'] = message_id

    data_id = job.get('payload', {}).get('properties', {}).get('data_id')
    result['data_id'] = data_id

    filehash = job.get('payload', {}).get('properties', {}).get('integrity', {}).get('value')  # noqa
    result['filehash'] = filehash

    metadata_id = job.get('payload', {}).get('properties', {}).get("metadata_id")
    result['metadata_id'] = metadata_id

    geometry = job.get('payload', {}).get('geometry')  # GeoJSON geometry dict or None

    result['broker'] = job['_broker']
    result['received'] = job['_received']
    result['queued'] = job['_queued']

    # deduplication step
    for key, type in [(message_id, 'by-msg-id'), (data_id, 'by-data-id'), (filehash, 'by-hash')]:
        if key:
            status = get_status(key, type)
            if status and status == STATUS_SUCCESS:
                LOGGER.debug(f"ID '{key}' ({type}) previously processed with status '{status}'")
                result['status'] = STATUS_SKIPPED
                result['reason'] = f"ID '{key}' ({type}) previously processed with status '{status}'"
                result['error_class'] = "PreviouslyProcessed"
                # Record the skip only for message_id (unique per notification)
                # so callers polling by-msg-id can observe the result.
                # data_id and filehash must keep their existing SUCCESS status
                # so that future duplicate messages are still caught by dedup.
                set_status(message_id, 'by-msg-id', STATUS_SKIPPED)
                return result

    # !! ToDo - the logic here needs checking !!
    # acquire lock on ID to make sure we only process once.
    lock_key_identifier = filehash or data_id or message_id
    lock_key = f"wis2:notification:data:lock:{lock_key_identifier}"
    redis_client = get_redis_client()
    lock_acquired = redis_client.set(lock_key, 1, nx=True, ex=LOCK_EXPIRE)
    if not lock_acquired:  # lock acquired by another worker
        LOGGER.debug(f"Could not acquire lock for {lock_key_identifier}, retrying in 10 seconds")
        try:
            raise self.retry(countdown=10, max_retries=10)
        except MaxRetriesExceededError:
            LOGGER.warning(f"Max retries exceeded waiting for lock on {lock_key_identifier}")
            result['status'] = STATUS_FAILED
            result['reason'] = f"Could not acquire lock for {lock_key_identifier} after max retries"
            result['error_class'] = "LockAcquisitionError"
            return result

    # At this point, we have not seen the ID before, and we have lock on ID.
    # Now attempt download
    try:
        # Now parse download URL from payload link
        download_url, expected_length, overwrite = _select_download_link(job.get('payload', {}).get('links', {}))
        result['download_url'] = download_url

        # check we have a download URL
        if not download_url:
            result['status'] = STATUS_SKIPPED
            result['reason'] = "No download URL in notification message"
            result['error_class'] = "MissingDownloadURLError"
            return result

        # prepare filepath
        today = dt.date.today()
        target_directory = Path(CONTAINER_DATA_PATH) / job.get("target", "") / f"{today:%Y/%m/%d}"
        target_directory.mkdir(exist_ok=True, parents=True)
        filename = os.path.basename(urlsplit(download_url).path)
        output_path = target_directory / filename
        # Check for directory traversal
        if target_directory.resolve() != output_path.resolve().parent:
            result['status'] = STATUS_FAILED
            result['reason'] = f"Invalid target directory {target_directory}"
            result['error_class'] = "InvalidTargetDirectory"
            return result

        # store output path in result
        result['filepath'] = str(output_path)

        # extract cache
        result['global_cache'] = urlsplit(download_url).hostname

        if result['global_cache'] in CACHE_EXCLUDE_LIST:
            result['status'] = STATUS_SKIPPED
            result['reason'] = "Global cache black listed, skipped"
            result['error_class'] = "GlobalCacheBlacklisted"
            LOGGER.debug(f"File {output_path} skipped from blacklisted cache")
            return result

        # Pre-download filter: evaluate rules against what is known before fetching.
        # Rules that depend on media_type or actual size won't fire here (those
        # fields are None at this point) and will be re-evaluated post-download.
        filter_config = job.get('filter') or {}
        notification_props = job.get('payload', {}).get('properties', {})
        pre_ctx = MatchContext(
            topic=topic,
            centre_id=centre_id if centre_id != 'unknown' else None,
            data_id=data_id,
            metadata_id=metadata_id,
            href=download_url,
            size=expected_length,
            geometry=geometry,
            properties=notification_props,
        )
        pre_action, pre_reason = _apply_job_filter(filter_config, pre_ctx)
        if pre_action == 'reject':
            result['status'] = STATUS_SKIPPED
            result['reason'] = pre_reason or "Rejected by pre-download filter"
            result['error_class'] = "FilterRejected"
            LOGGER.info(f"File {output_path} rejected pre-download: {pre_reason} (filter: {filter_config})")
            return result

        # check if the file exists, if so we have already processed this notification
        if output_path.exists() and not overwrite:
            result['status'] = STATUS_SKIPPED
            result['reason'] = "File already exists and overwrite is not requested"
            result['error_class'] = "FileExistsError"
            LOGGER.debug(f"File {output_path} already exists, skipping")
            return result

        # Validate hash method before downloading to avoid wasting bandwidth on
        # an unsupported method.
        hash_props = job.get('payload', {}).get('properties', {}).get('integrity', {})
        hash_method = hash_props.get('method', 'sha512')
        hash_expected = hash_props.get('value')
        result['hash_method'] = hash_method
        result['expected_hash'] = hash_expected

        hasher = None
        if hash_method:
            sanitized_method = hash_method.replace('-', '_')
            if sanitized_method not in ALLOWED_HASH_METHODS:
                result['status'] = STATUS_SKIPPED
                result['reason'] = "Invalid hash method"
                result['error_class'] = "InvalidHashMethod"
                LOGGER.warning(
                    "File %s skipped, invalid hash method '%s'", output_path, sanitized_method)
                return result
            hash_fn = getattr(hash_module, sanitized_method, None)
            if not hash_fn:
                result['status'] = STATUS_SKIPPED
                result['reason'] = "Hash method not found"
                result['error_class'] = "InvalidHashMethod"
                LOGGER.warning(
                    "File %s skipped, hash method '%s' not found", output_path, sanitized_method)
                return result
            hasher = hash_fn()

        # Stream the download directly to a temp file to avoid loading large
        # files into memory.  The hash is computed incrementally and the MIME
        # type is detected from the first chunk.
        result['status'] = STATUS_PENDING
        result['download_start'] = _now_utc_str()
        response = None
        tmp_path = None
        try:
            try:
                response = _pool.request(
                    'GET', download_url,
                    headers=_build_auth_headers(job.get('credentials')),
                    preload_content=False,
                    timeout=urllib3.Timeout(connect=5.0, read=60.0),
                )
            except urllib3.exceptions.ConnectTimeoutError as e:
                result['status'] = STATUS_FAILED
                result['reason'] = f"Connection timeout error for {result['global_cache']}, see logs"
                result['error_class'] = str(e.__class__.__name__)
                LOGGER.warning("Connection timeout %s for %s", e, result['global_cache'])
                return result
            except urllib3.exceptions.ReadTimeoutError as e:
                result['status'] = STATUS_FAILED
                result['reason'] = f"Download timeout error for {result['global_cache']}, see logs"
                result['error_class'] = str(e.__class__.__name__)
                LOGGER.warning("Read timeout %s for %s", e, result['global_cache'])
                return result
            except urllib3.exceptions.MaxRetryError as e:
                result['status'] = STATUS_FAILED
                result['reason'] = f"Maximum retries downloading from {result['global_cache']} exceeded"
                result['error_class'] = str(e.__class__.__name__)
                return result
            except Exception as e:
                result['status'] = STATUS_FAILED
                result['reason'] = f"Error while downloading from {result['global_cache']}, see logs"
                result['error_class'] = str(e.__class__.__name__)
                LOGGER.warning("Error %s while downloading from %s", e, result['global_cache'])
                return result

            if response.status != 200:
                if response.status in RETRYABLE_HTTP_CODES:
                    countdown = min(2 ** self.request.retries * 5, 300)
                    LOGGER.warning(
                        "HTTP %d from %s, retry %d in %ds",
                        response.status, result['global_cache'],
                        self.request.retries + 1, countdown,
                    )
                    raise self.retry(countdown=countdown, max_retries=5)
                result['status'] = STATUS_FAILED
                result['reason'] = f"HTTP {response.status} response from {result['global_cache']}"
                result['error_class'] = "HTTPError"
                LOGGER.warning("HTTP %d (non-retryable) downloading %s", response.status, download_url)
                return result

            # Stream response body to a temp file.
            fh, tmp_path = tempfile.mkstemp(dir=target_directory, prefix='.tmp_')
            os.close(fh)
            try:
                actual_size, mime_type = _stream_response_to_file(
                    response, tmp_path, hasher, download_url
                )
            except urllib3.exceptions.ReadTimeoutError as e:
                result['status'] = STATUS_FAILED
                result['reason'] = f"Read timeout during download from {result['global_cache']}, see logs"
                result['error_class'] = str(e.__class__.__name__)
                LOGGER.warning("Read timeout during streaming from %s: %s", result['global_cache'], e)
                return result
            except OSError as e:
                result['status'] = STATUS_FAILED
                result['reason'] = "Failed to write file during download, see logs"
                result['error_class'] = str(e.__class__.__name__)
                LOGGER.error("Disk error streaming %s to %s: %s", download_url, tmp_path, e)
                return result
            except Exception as e:
                result['status'] = STATUS_FAILED
                result['reason'] = f"Error during download from {result['global_cache']}, see logs"
                result['error_class'] = str(e.__class__.__name__)
                LOGGER.warning("Error streaming from %s: %s", result['global_cache'], e)
                return result

        finally:
            if response is not None:
                response.release_conn()
            # Clean up any partial temp file on failure
            if result.get('status') == STATUS_FAILED and tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
                tmp_path = None

        result['download_end'] = _now_utc_str()
        result['actual_filesize'] = actual_size
        result['media_type'] = mime_type

        # Post-download filter: re-evaluate with full context (media_type and actual size now known).
        post_ctx = MatchContext(
            topic=topic,
            centre_id=centre_id if centre_id != 'unknown' else None,
            data_id=data_id,
            metadata_id=metadata_id,
            href=download_url,
            media_type=mime_type,
            size=actual_size,
            geometry=geometry,
            properties=notification_props,
        )
        post_action, post_reason = _apply_job_filter(filter_config, post_ctx)
        if post_action == 'reject':
            Path(tmp_path).unlink(missing_ok=True)
            result['status'] = STATUS_SKIPPED
            result['reason'] = post_reason or "Rejected by post-download filter"
            result['error_class'] = "FilterRejected"
            LOGGER.info(
                "File %s rejected post-download: %s (filter: %s, media_type: %s)",
                output_path, post_reason, filter_config, mime_type,
            )
            return result

        # Hash verification using the incrementally computed digest.
        if hasher is not None:
            hash_base64 = base64.b64encode(hasher.digest()).decode()
            result['actual_hash'] = hash_base64
            if hash_expected:
                result['valid_hash'] = (hash_base64 == hash_expected)
                if not result['valid_hash']:
                    Path(tmp_path).unlink(missing_ok=True)
                    LOGGER.warning("Hash verification failed for %s (%s)", download_url, data_id)
                    result['status'] = STATUS_SKIPPED
                    result['reason'] = f"Hash verification failed for {download_url}"
                    result['error_class'] = "HashVerificationError"
                    return result

        # Atomically move temp file to its final location.
        try:
            if overwrite:
                os.replace(tmp_path, output_path)
            else:
                try:
                    os.link(tmp_path, output_path)
                    Path(tmp_path).unlink(missing_ok=True)
                except FileExistsError:
                    Path(tmp_path).unlink(missing_ok=True)
                    result['status'] = STATUS_SKIPPED
                    result['reason'] = "File created by another process"
                    result['error_class'] = "FileExistsError"
                    LOGGER.debug("File %s already exists (race condition), skipping", output_path)
                    return result
        except OSError as e:
            Path(tmp_path).unlink(missing_ok=True)
            result['status'] = STATUS_FAILED
            result['reason'] = "Failed to write file, see logs"
            result['error_class'] = str(e.__class__.__name__)
            LOGGER.error("Failed to move %s to %s: %s", tmp_path, output_path, e)
            return result

        result['save'] = True
        result['status'] = STATUS_SUCCESS

        LOGGER.debug(result)
        return result

    except Retry:
        raise
    except MaxRetriesExceededError:
        LOGGER.warning(f"Max retries exceeded for HTTP error downloading {download_url}")
        result['status'] = STATUS_FAILED
        result['reason'] = f"Max retries exceeded for HTTP error from {result['global_cache']}"
        result['error_class'] = "HTTPError"
        return result
    except Exception as e:
        LOGGER.error(f"Error processing job {message_id}: {e}", exc_info=True)
        result['status'] = STATUS_FAILED
        result['reason'] = f"Error processing job {message_id}, see logs"
        result['error_class'] = str(e.__class__.__name__)
        return result

    finally:
        if lock_acquired:
            redis_client.delete(lock_key)
        final_status = result.get('status', STATUS_FAILED)
        set_status(message_id, 'by-msg-id', final_status)
        set_status(data_id, 'by-data-id', final_status)
        set_status(filehash, 'by-hash', final_status)


# @ prov_dm_wrapper
@app.task
def decode_and_ingest(result):
    if result.get('status') != STATUS_SUCCESS:
        LOGGER.debug(
            f"Skipping decode for job {result.get('id')} due to previous status: {result.get('status')}")
        return result

    LOGGER.info(f"Starting decode and ingest for {result.get('filepath')}")
    # Add your data decoding and ingestion logic here
    return result
