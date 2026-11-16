from celery import Celery
import os
import sys

from shared.logging import setup_logging
from shared.valkey_client import (VALKEY_HOST, VALKEY_PORT, VALKEY_PASSWORD)
from shared.queues import DEFAULT_QUEUE
from shared.config_check import Setting, VALKEY_SETTINGS, require_settings

# Set up logging
setup_logging()  # Configure root logger
LOGGER = setup_logging(__name__)

require_settings('celery-worker', (
    *VALKEY_SETTINGS,
    *(Setting(name, integer=True) for name in (
        'CELERY_BACKEND_DB', 'CELERY_RESULT_DB', 'VALKEY_TTL_SECONDS', 'VALKEY_MESSAGE_LOCK',
        'DOWNLOAD_MAX_SECONDS', 'DOWNLOAD_CHUNK_SIZE')),
))

CELERY_BACKEND_DB = int(os.getenv("CELERY_BACKEND_DB", "0"))
CELERY_RESULT_DB = int(os.getenv("CELERY_RESULT_DB", "1"))

# kombu has no valkey:// transport yet (celery/kombu#2246)
CELERY_BROKER_URL = f"redis://:{VALKEY_PASSWORD}@{VALKEY_HOST}:{VALKEY_PORT}/{CELERY_BACKEND_DB}"
CELERY_RESULT_BACKEND = f"redis://:{VALKEY_PASSWORD}@{VALKEY_HOST}:{VALKEY_PORT}/{CELERY_RESULT_DB}"

# --- Celery App Setup ---
app = Celery('tasks',
             broker=CELERY_BROKER_URL,
             result_backend=CELERY_RESULT_BACKEND)

app.conf.worker_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
app.conf.result_expires = 300
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_default_queue=DEFAULT_QUEUE,
)

# Import your tasks
app.autodiscover_tasks(['task_manager.tasks', 'task_manager.tasks.wis2'])


def main():
    app.start(argv=sys.argv[1:])


if __name__ == '__main__':
    main()
