from celery import Celery
import os
import sys

from shared import setup_logging

# Set up logging
setup_logging()  # Configure root logger
LOGGER = setup_logging(__name__)

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND",
                                       "redis://redis:6379/1")
# --- Celery App Setup ---
app = Celery('tasks',
             broker=CELERY_BROKER_URL,
             result_backend=CELERY_RESULT_BACKEND)

app.conf.worker_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()

# Import your tasks
app.autodiscover_tasks(['task_manager.tasks','task_manager.tasks.wis2' ])

def main():
    app.start(argv=sys.argv[1:])

if __name__ == '__main__':
    main()