from celery.utils.log import get_task_logger
from celery import Celery
from celery.schedules import crontab
import datetime as dt
import os
import shutil

from task_manager.scheduler import app as app

# Import shared utilities
from shared import set_gauge, incr_counter

LOGGER = get_task_logger(__name__)

CONTAINER_DATA_PATH = os.getenv("CONTAINER_DATA_PATH", "/data")  # this needs checking
RETENTION_PERIOD_HOURS = int(os.environ.get('DOWNLOAD_RETENTION_PERIOD', 30)) * 24  # noqa


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    # Calls clean_directory(CONTAINER_DATA_PATH) daily at 00:15 UTC.
    sender.add_periodic_task(crontab(hour=0, minute=15), clean_directory.s(CONTAINER_DATA_PATH),
                             name='clean downloads daily')
    # Check for disk space every 5 minutes creating a metric and log a warning if available space is below threshold
    sender.add_periodic_task(300.0, check_disk_space.s(), name='check disk space every 5 minutes')
    # Recalibrate downloads size gauge once per day
    sender.add_periodic_task(86400.0, recalibrate_downloads_size.s(), name='recalibrate downloads size daily')


@app.task
def check_disk_space():
    """Check disk space and log a warning if available space is below threshold."""
    try:
        total, used, free = shutil.disk_usage(CONTAINER_DATA_PATH)
        percent_free = free / total * 100
        set_gauge('disk_total_bytes', {}, total)
        set_gauge('disk_used_bytes', {}, used)
        set_gauge('disk_free_bytes', {}, free)
        LOGGER.debug(f"Disk usage for {CONTAINER_DATA_PATH}: {percent_free:.2f}% free")
        # You can set a threshold for warning, e.g., 20%
        if percent_free < 20:
            LOGGER.warning(f"Disk usage for {CONTAINER_DATA_PATH} is below 20%: {percent_free:.2f}% free")
    except Exception as e:
        LOGGER.error(f"Error checking disk space: {e}", exc_info=True)


def _as_date(year: str, month: str, day: str) -> dt.date | None:
    """Return the date named by a YYYY/MM/DD path, or None if it is not one."""
    if not (len(year) == 4 and len(month) == 2 and len(day) == 2):
        return None
    try:
        return dt.date(int(year), int(month), int(day))
    except ValueError:
        return None


def _delete_day_directory(path: str) -> tuple[int, int]:
    """Delete a day directory and its contents, returning (no. of files removed, bytes freed)."""
    files_removed = 0
    bytes_freed = 0
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                size = os.path.getsize(file_path)
                os.remove(file_path)
            except FileNotFoundError:
                continue
            files_removed += 1
            bytes_freed += size
        for dirname in dirnames:
            os.rmdir(os.path.join(dirpath, dirname))
    os.rmdir(path)
    return files_removed, bytes_freed


def _find_expired_day_directories(directory: str, cutoff: dt.date, parents: tuple[str, ...] = ()):
    """Yield {target}/YYYY/MM/DD directories dated before cutoff."""
    with os.scandir(directory) as entries:
        subdirs = [e for e in entries if e.is_dir(follow_symlinks=False)]
    for entry in subdirs:
        day = _as_date(*parents[-2:], entry.name) if len(parents) >= 2 else None
        if day is not None:
            if day < cutoff:
                yield entry.path
        else:
            yield from _find_expired_day_directories(entry.path, cutoff, parents + (entry.name,))


@app.task
def clean_directory(directory):
    """Delete day directories older than the retention period."""
    # Delete days before the cutoff date (UTC)
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = (now - dt.timedelta(hours=RETENTION_PERIOD_HOURS)).date()

    files_removed = 0
    bytes_freed = 0
    directories_removed = 0
    for day_path in list(_find_expired_day_directories(directory, cutoff)):
        try:
            removed, freed = _delete_day_directory(day_path)
        except OSError as e:
            LOGGER.error(f"CLEANER: error removing {day_path}: {e}")
            continue
        files_removed += removed
        bytes_freed += freed
        directories_removed += 1
        # Remove the month and year directories if now empty
        parent = os.path.dirname(day_path)
        for _ in range(2):
            try:
                os.rmdir(parent)
            except OSError:
                break
            directories_removed += 1
            parent = os.path.dirname(parent)

    if bytes_freed:
        incr_counter('disk_downloads_bytes', {}, -bytes_freed)
    LOGGER.debug(f'CLEANER: removed {files_removed} old files and {directories_removed} directories')  # noqa


@app.task
def recalibrate_downloads_size():
    """Recompute the downloads directory size from disk and correct the Valkey gauge."""
    try:
        actual_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(CONTAINER_DATA_PATH)
            for filename in filenames
        )
        set_gauge('disk_downloads_bytes', {}, actual_size)
        LOGGER.debug(f"Recalibrated disk_downloads_bytes to {actual_size} bytes")
    except Exception as e:
        LOGGER.error(f"Error recalibrating downloads size: {e}", exc_info=True)
