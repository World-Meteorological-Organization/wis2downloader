from celery.utils.log import get_task_logger
from celery import Celery
import os
import time
import shutil

from task_manager.scheduler import app as app

# Import shared utilities
from shared import set_gauge, incr_counter

LOGGER = get_task_logger(__name__)

CONTAINER_DATA_PATH = os.getenv("CONTAINER_DATA_PATH","/data") # this needs checking
RETENTION_PERIOD_HOURS = int(os.environ.get('DOWNLOAD_RETENTION_PERIOD', 30)) * 24  # noqa


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    # Calls clean_directory(CONTAINER_DATA_PATH) every 10 minute.
    sender.add_periodic_task(600.0, clean_directory.s(CONTAINER_DATA_PATH), name='clean downloads every 10 minutes')
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
                incr_counter('disk_downloads_bytes', {}, -os.path.getsize(file_path))
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


@app.task
def recalibrate_downloads_size():
    """Recompute the downloads directory size from disk and correct the Redis gauge."""
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
