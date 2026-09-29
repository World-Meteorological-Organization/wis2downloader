"""Shared utilities for wis2downloader modules."""

# Version of the shared utilities. This can be used by other modules to ensure compatibility.
__version__ = "1.0.0b1+rc4"

from .valkey_client import get_valkey_client
from .logging import setup_logging
from .filters import apply_filters, MatchContext
from .valkey_metrics import incr_counter, set_gauge, generate_prometheus_text
from .queues import VALID_QUEUES, DEFAULT_QUEUE

__all__ = [
    '__version__',
    'get_valkey_client', 'setup_logging',
    'apply_filters', 'MatchContext',
    'incr_counter', 'set_gauge', 'generate_prometheus_text',
    'VALID_QUEUES', 'DEFAULT_QUEUE',
]
