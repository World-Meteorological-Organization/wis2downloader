from celery.utils.log import get_task_logger
from celery import Celery
from fnmatch import fnmatch
from functools import wraps
import importlib
import magic
import mimetypes
import os
from pathlib import Path
import time
import urllib3
from urllib.parse import urlsplit
import shutil

from housekeep_manager.worker import app as app

# Import shared utilities
from shared import get_redis_client, apply_filters, MatchContext, incr_counter, set_gauge

LOGGER = get_task_logger(__name__)

DATA_BASEPATH = os.getenv("DATA_BASEPATH","/data") # this needs checking
RETENTION_PERIOD_HOURS = int(os.environ.get('DOWNLOAD_RETENTION_PERIOD', 30)) * 24  # noqa

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

_pool = urllib3.PoolManager()
hash_module = importlib.import_module("hashlib")


TRACKER = "wis2:notifications:data:tracker"

mimetypes.add_type('application/bufr', '.bufr')
mimetypes.add_type('application/grib', '.grib')

DEFAULT_ACCEPTED_MEDIA_TYPES = [
                        'image/gif', 'image/jpeg', 'image/png', 'image/tiff',  # image formats
                        'application/pdf', 'application/postscript',  # postscript and PDF
                        'application/bufr', 'application/grib',  # WMO formats
                        'application/x-hdf', 'application/x-hdf5', 'application/x-netcdf', 'application/x-netcdf4',  # scientific formats
                        'text/plain', 'text/html', 'text/xml', 'text/csv', 'text/tab-separated-values',  # text based formats
                        'application/octet-stream',
                        ]


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

        except Exception as e:
            LOGGER.error(f"Error collecting metrics: {e}", exc_info=True)

        return result
    return wrapper

@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    # Calls clean_directory(DATA_BASEPATH) every 10 minute.
    sender.add_periodic_task(600.0, clean_directory.s(DATA_BASEPATH), name='clean downloads every 10 minutes')
    # Check for disk space every 5 minutes creating a metric and log a warning if available space is below threshold
    sender.add_periodic_task(300.0, check_disk_space.s(), name='check disk space every 5 minutes')

@app.task
def check_disk_space():
    """Check disk space and log a warning if available space is below threshold."""
    try:
        total, used, free = shutil.disk_usage(DATA_BASEPATH)
        percent_free = free / total * 100
        set_gauge('free_space', {}, percent_free)
        LOGGER.debug(f"Disk usage for {DATA_BASEPATH}: {percent_free:.2f}% free")
        # You can set a threshold for warning, e.g., 20%
        if percent_free < 20:
            LOGGER.warning(f"Disk usage for {DATA_BASEPATH} is below 20%: {percent_free:.2f}% free")
    except Exception as e:
        LOGGER.error(f"Error checking disk space: {e}", exc_info=True)


@app.task
def clean_directory(directory):
    # get the current time
    current_time = time.time()

    files_removed = 0
    directories_removed = 0
    # loop through the files in the directory, including subdirectories
    for file in os.listdir(directory):
        # get the full path of the file
        file_path = os.path.join(directory, file)
        # check if the path is a file or a directory
        if os.path.isfile(file_path):
            # get the time the file was last modified
            file_time = os.path.getmtime(file_path)
            # check if the file is older than the retention period
            if current_time - file_time > RETENTION_PERIOD_HOURS * 3600:
                os.remove(file_path)
                files_removed += 1
        elif os.path.isdir(file_path):
            # recursively clean the directory
            clean_directory(file_path)
            # if the directory is empty, remove it
            if not os.listdir(file_path):
                os.rmdir(file_path)
                directories_removed += 1
    LOGGER.debug(f'CLEANER: removed {files_removed} old files and {directories_removed} empty directories')  # noqa
