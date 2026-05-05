from celery import Celery
import os
import sys

from shared.logging import setup_logging
from shared.redis_client import (REDIS_HOST, REDIS_PORT, REDIS_PASSWORD)

# Set up logging
setup_logging()  # Configure root logger
LOGGER = setup_logging(__name__)

if not REDIS_PASSWORD:
    raise ValueError("REDIS_PASSWORD must be set")

SCHEDULER_BACKEND_DB = int(os.getenv("SCHEDULER_BACKEND_DB", "2"))
SCHEDULER_RESULT_DB = int(os.getenv("SCHEDULER_RESULT_DB", "3"))

SCHEDULER_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{SCHEDULER_BACKEND_DB}"
SCHEDULER_RESULT_BACKEND = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{SCHEDULER_RESULT_DB}"

# --- Celery App Setup ---
app = Celery('tasks',
             broker=SCHEDULER_BROKER_URL,
             result_backend=SCHEDULER_RESULT_BACKEND)
app.conf.worker_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
app.conf.CELERYBEAT_LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
app.conf.result_expires = 86400  # 1 day, or do we want 1 hour? (TBD)
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json'
)

# Import your tasks
app.autodiscover_tasks(['task_manager.tasks', 'task_manager.tasks.scheduled_tasks'])


def main():
    app.start(argv=sys.argv[1:])


if __name__ == '__main__':
    main()
