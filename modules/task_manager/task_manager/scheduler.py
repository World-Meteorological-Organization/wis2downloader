from celery import Celery
import os
import sys

from shared.logging import setup_logging
from shared.valkey_client import (VALKEY_HOST, VALKEY_PORT, VALKEY_PASSWORD)
from shared.config_check import Setting, VALKEY_SETTINGS, require_settings

# Set up logging
setup_logging()  # Configure root logger
LOGGER = setup_logging(__name__)

require_settings('celery-scheduler', (
    *VALKEY_SETTINGS,
    *(Setting(name, integer=True) for name in (
        'SCHEDULER_BACKEND_DB', 'SCHEDULER_RESULT_DB', 'DOWNLOAD_RETENTION_PERIOD')),
))

SCHEDULER_BACKEND_DB = int(os.getenv("SCHEDULER_BACKEND_DB", "2"))
SCHEDULER_RESULT_DB = int(os.getenv("SCHEDULER_RESULT_DB", "3"))

# kombu has no valkey:// transport yet (celery/kombu#2246)
SCHEDULER_BROKER_URL = f"redis://:{VALKEY_PASSWORD}@{VALKEY_HOST}:{VALKEY_PORT}/{SCHEDULER_BACKEND_DB}"
SCHEDULER_RESULT_BACKEND = f"redis://:{VALKEY_PASSWORD}@{VALKEY_HOST}:{VALKEY_PORT}/{SCHEDULER_RESULT_DB}"

# --- Celery App Setup ---
app = Celery('tasks',
             broker=SCHEDULER_BROKER_URL,
             result_backend=SCHEDULER_RESULT_BACKEND)
app.conf.worker_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
app.conf.CELERYBEAT_LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
app.conf.result_expires = 300
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_soft_time_limit=3000,
    task_time_limit=3600,
)

# Import your tasks
app.autodiscover_tasks(['task_manager.tasks', 'task_manager.tasks.scheduled_tasks'])


def main():
    app.start(argv=sys.argv[1:])


if __name__ == '__main__':
    main()
