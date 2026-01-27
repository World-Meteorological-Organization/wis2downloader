import logging
import os

from .manager import run_manager

LOGGER = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL","DEBUG").upper()
LOGGER.setLevel(LOG_LEVEL)

def main():
    LOGGER.info("Starting subscriber")
    run_manager()

if __name__ == "__main__":
    main()