__version__ = "v0.2.0"
from flask import request
import json
import logging
import os
import threading
from urllib.parse import unquote
from uuid import uuid4
from .subscriber import Subscriber

# Setup defaults for the subscription manager package
DEFAULT_FLASK_HOST = "0.0.0.0"
DEFAULT_FLASK_PORT = 5001
DEFAULT_BROKER_HOST = "globalbroker.meteo.fr"
DEFAULT_BROKER_PORT = 443
DEFAULT_USERNAME = "everyone"
DEFAULT_PASSWORD = "everyone"
DEFAULT_PROTOCOL = "websockets"

# get logger
LOGGER = logging.getLogger(__name__)

# global lock to protect the config file
CONFIG_FILE_LOCK = threading.Lock()
# Now get the config file path
CONFIG_PATH = os.getenv("CONFIG_PATH", "/app/config/config.json")

SUBSCRIBERS: dict[str, Subscriber] = {}
SUBSCRIBER_THREADS: dict[str, threading.Thread] = {}

def load_config() -> dict:
    CONFIG_FILE_LOCK.acquire()
    try:
        if not os.path.exists(CONFIG_PATH):
            LOGGER.warning(f"Config file {CONFIG_PATH} not found, using defaults")
            return {"brokers": {}, "topics": {}, "flask_host": DEFAULT_FLASK_HOST,
                    "flask_port": DEFAULT_FLASK_PORT}
        with open(CONFIG_PATH) as fh:
            try:
                _config = json.load(fh)
                _config.setdefault('brokers',{})
                _config.setdefault('topics',{})
                _config.setdefault('flask_host', DEFAULT_FLASK_HOST)
                _config.setdefault('flask_port', DEFAULT_FLASK_PORT)
                return _config
            except json.JSONDecodeError as e:
                LOGGER.error(f"Failed to load configuration file: {e}")
                return {"brokers": {}, "topics": {}, "flask_host": DEFAULT_FLASK_HOST,
                    "flask_port": DEFAULT_FLASK_PORT}
    finally:
        CONFIG_FILE_LOCK.release()


def save_config(config: dict) -> None:
    CONFIG_FILE_LOCK.acquire()
    _temp_file = CONFIG_PATH + ".temp"

    try:
        with open(_temp_file, 'w') as fh:
            fh.write(json.dumps(config, indent=4))
        os.replace(_temp_file, CONFIG_PATH)
    except Exception as e:
        LOGGER.error(f"Failed to save configuration file: {e}")
        if os.path.exists(_temp_file):
            os.remove(_temp_file)
            LOGGER.debug(f"Cleaned up temporary file: {_temp_file}")
    finally:
        CONFIG_FILE_LOCK.release()


def persist_config(config: dict) -> None:
    """Centralise config save and logging."""
    save_config(config)
    LOGGER.debug("Configuration persisted to disk")


def init_subscribers(config: dict) -> None:
    """Initialize broker connections and subscribe to configured topics."""
    for broker_name, broker_config in config.get('brokers', {}).items():
        session_id = broker_config.get('session', str(uuid4()))
        host = broker_config.get('host')
        port = broker_config.get('port')
        username = broker_config.get('username')
        password = broker_config.get('password')
        protocol = broker_config.get('protocol')

        if None in (host, port, username, password, protocol):
            LOGGER.error(f"Missing configuration for broker {broker_name}")
            continue

        SUBSCRIBERS[broker_name] = Subscriber(
            host=host, port=port, uid=username, pwd=password,
            protocol=protocol, session=session_id)

        # normalise and persist broker config back, required due to use of defaults
        config['brokers'][broker_name] = {
            'session': session_id, 'host': host, 'port': port,
            'username': username, 'password': password, 'protocol': protocol
        }

        # create thread and start
        thread = threading.Thread(target=SUBSCRIBERS[broker_name].start,
                                  daemon=True)
        SUBSCRIBER_THREADS[broker_name] = thread
        thread.start()

        # now subscribe to topics
        for _topic, _target in config.get('topics', {}).items():
            SUBSCRIBERS[broker_name].subscribe(_topic, _target)


def shutdown():
    """Shutdown all subscriber threads."""
    for broker_name, _subscriber in SUBSCRIBERS.items():
        _subscriber.stop()
        thread = SUBSCRIBER_THREADS[broker_name]
        thread.join(timeout=5)
        if thread.is_alive():
            LOGGER.error(f"Failed to shutdown subscriber thread for {broker_name} gracefully")

