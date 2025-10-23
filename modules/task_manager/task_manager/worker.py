# task_manager/worker.py
import logging
import os
from celery import Celery
import sys
import time
# set up logging
log_formatter = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03dZ, %(name)s, %(levelname)s, %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
log_formatter.converter = time.gmtime

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG").upper())
root_logger.addHandler(stream_handler)
LOGGER = logging.getLogger(__name__)

# Load celery broker details from ENV.
CELERY_BROKER = os.environ.get("CELERY_BROKER", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

# Setup app

app = Celery('tasks',
             broker=CELERY_BROKER,
             result_backend=CELERY_RESULT_BACKEND)

# Import your tasks
app.autodiscover_tasks(['task_manager.tasks','task_manager.tasks.wis2' ])

def main():
    app.start(argv=sys.argv[1:])

if __name__ == '__main__':
    main()
