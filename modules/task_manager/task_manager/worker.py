import logging
import os
import sys
import time
import json # New import required for parsing transport options
from celery import Celery

# set up logging
log_formatter = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03dZ, %(name)s, %(levelname)s, %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
log_formatter.converter = time.gmtime

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
# Use LOG_LEVEL from environment for root logger
root_logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG").upper())
root_logger.addHandler(stream_handler)
LOGGER = logging.getLogger(__name__)


# 1. Load Celery Broker URL (Sentinel list)
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL", 
    "sentinel://redis-sentinel-1:26379;sentinel://redis-sentinel-2:26379;sentinel://redis-sentinel-3:26379/0"
)

# 2. Load Celery Broker Transport Options (including 'master_name')
CELERY_BROKER_TRANSPORT_OPTIONS_STR = os.environ.get(
    "CELERY_BROKER_TRANSPORT_OPTIONS", 
    '{"master_name": "redis-primary",'
    '"socket_connect_timeout": 1,'
    '"socket_timeout": 1,'
    '"retry_on_timeout": True,'
    '"retry_errors": ["BusyLoadingError"]}'
)
try:
    CELERY_BROKER_TRANSPORT_OPTIONS = json.loads(CELERY_BROKER_TRANSPORT_OPTIONS_STR)
except json.JSONDecodeError:
    LOGGER.warning("Could not parse CELERY_BROKER_TRANSPORT_OPTIONS. Using default.")
    CELERY_BROKER_TRANSPORT_OPTIONS = {"master_name": "redis-primary"}


# 3. Load Celery Result Backend URL (Sentinel list)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", 
    "sentinel://redis-sentinel-1:26379;sentinel://redis-sentinel-2:26379;sentinel://redis-sentinel-3:26379/1"
)

# 4. Load Celery Result Backend Transport Options
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS_STR = os.environ.get(
    "CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS", 
    '{"master_name": "redis-primary"}'
)
try:
    CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = json.loads(CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS_STR)
except json.JSONDecodeError:
    LOGGER.warning("Could not parse CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS. Using default.")
    CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {"master_name": "redis-primary"}


# --- Celery App Setup ---

app = Celery('tasks',
             broker=CELERY_BROKER_URL,
             result_backend=CELERY_RESULT_BACKEND)

# Apply the Sentinel-specific options to the Celery app
app.conf.broker_transport_options = CELERY_BROKER_TRANSPORT_OPTIONS
app.conf.result_backend_transport_options = CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS

# Optionally set LOG_LEVEL for visibility
app.conf.worker_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()


# Import your tasks
app.autodiscover_tasks(['task_manager.tasks','task_manager.tasks.wis2' ])

def main():
    app.start(argv=sys.argv[1:])

if __name__ == '__main__':
    main()