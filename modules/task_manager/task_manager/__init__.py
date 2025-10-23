from functools import wraps
from celery import current_task
import datetime as dt
import json
from celery.utils.log import get_task_logger

__version__ = "0.0.1"

LOGGER = get_task_logger(__name__)
