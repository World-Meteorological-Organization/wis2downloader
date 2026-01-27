import logging
import os
import threading
import time
from uuid import uuid4

from .command_listener import CommandListener
from .subscriber import Subscriber

LOGGER = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
LOGGER.setLevel(LOG_LEVEL)

COMMAND_CHANNEL = "subscription_commands"


def run_manager():
    broker_config = {
        'host': os.getenv("GLOBAL_BROKER_HOST"),
        'port': int(os.getenv("GLOBAL_BROKER_PORT", 443)),
        'uid': os.getenv("GLOBAL_BROKER_USERNAME", "everyone"),
        'pwd': os.getenv("GLOBAL_BROKER_PASSWORD", "everyone"),
        'protocol': os.getenv("MQTT_PROTOCOL", "websockets"),
        'session': os.getenv("MQTT_SESSION_ID", str(uuid4()))
    }

    if not broker_config.get('host'):
        LOGGER.error("No broker host provided, exiting")
        return

    mqtt_subscriber = Subscriber(**broker_config)

    redis_listener = CommandListener(
        subscriber=mqtt_subscriber,
        channel=COMMAND_CHANNEL
    )

    mqtt_thread = threading.Thread(target=mqtt_subscriber.start, daemon = True)
    mqtt_thread.start()

    redis_listener.start()

    LOGGER.info(f"Subscription manager started for broker: {broker_config.get('host')}")

    try:
        while True:
            time.sleep(1)
            if not mqtt_thread.is_alive():
                LOGGER.critical("MQTT thread died! Shutting down process.")
                break

    except KeyboardInterrupt:
        LOGGER.info("Received keyboard interrupt, shutting down")

    finally:
        LOGGER.info("Shutting down subscription manager")
        redis_listener.stop()
        mqtt_subscriber.stop()
        mqtt_thread.join(timeout=60)
        LOGGER.info("Subscription manager shutdown complete")