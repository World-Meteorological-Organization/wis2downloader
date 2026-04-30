import json
import os
import signal
import sys
import threading
import time
from uuid import uuid4

from .command_listener import CommandListener
from .subscriber import Subscriber
from shared import setup_logging, get_redis_client

LOGGER = setup_logging(__name__)

COMMAND_CHANNEL = "subscription_commands"

GLOBAL_SUBSCRIPTIONS_KEY = "global:subscriptions"
LEGACY_TOPICS_KEY = "global:topics"
LEGACY_SUBSCRIPTION_KEY = "global:all_subscriptions"


def _migrate_legacy_subscriptions(redis_client) -> dict:
    """Migrate from global:topics or global:all_subscriptions to global:subscriptions.

    Checks global:topics first (intermediate format), then falls back to
    global:all_subscriptions (original format).

    Returns a dict of {sub_id: sub_data} for the migrated entries.
    """
    # Try global:topics (intermediate format from previous refactor)
    topics_data = redis_client.hgetall(LEGACY_TOPICS_KEY)
    if topics_data:
        migrated = {}
        for topic_bytes, data_bytes in topics_data.items():
            topic = topic_bytes.decode('utf-8')
            try:
                topic_data = json.loads(data_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                LOGGER.warning(f"Could not decode topic data for {topic}, skipping")
                continue
            for dest_id, dest in topic_data.get('destinations', {}).items():
                sub_data = {
                    'id': dest_id,
                    'topic': topic,
                    'save_path': dest.get('save_path'),
                    'filter': dest.get('filter', {}),
                }
                migrated[dest_id] = sub_data
                redis_client.hset(GLOBAL_SUBSCRIPTIONS_KEY, dest_id, json.dumps(sub_data))
                LOGGER.info(f"Migrated subscription {dest_id} (topic: {topic})")
        return migrated

    # Fall back to global:all_subscriptions (original format)
    legacy_data = redis_client.hgetall(LEGACY_SUBSCRIPTION_KEY)
    if not legacy_data:
        return {}

    migrated = {}
    for topic_bytes, data_bytes in legacy_data.items():
        topic = topic_bytes.decode('utf-8')
        try:
            data = json.loads(data_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            LOGGER.warning(f"Could not decode legacy subscription for {topic}, skipping")
            continue
        sub_id = str(uuid4())
        sub_data = {
            'id': sub_id,
            'topic': topic,
            'save_path': data.get('save_path'),
            'filter': data.get('filters', {}),
        }
        migrated[sub_id] = sub_data
        redis_client.hset(GLOBAL_SUBSCRIPTIONS_KEY, sub_id, json.dumps(sub_data))
        LOGGER.info(f"Migrated legacy subscription for topic {topic} as {sub_id}")

    return migrated


def load_persisted_subscriptions(redis_client, mqtt_subscriber):
    """Load existing subscriptions from Redis on startup."""
    try:
        all_subs_raw = redis_client.hgetall(GLOBAL_SUBSCRIPTIONS_KEY)

        if not all_subs_raw:
            LOGGER.info(
                "global:subscriptions is empty — checking for legacy data to migrate")
            migrated = _migrate_legacy_subscriptions(redis_client)
            if not migrated:
                LOGGER.info("No persisted subscriptions found")
                return
            all_subs_raw = {
                k.encode(): json.dumps(v).encode()
                for k, v in migrated.items()
            }

        # Group subscriptions by topic to build per-topic dicts
        by_topic: dict[str, dict] = {}
        for sub_id_bytes, data_bytes in all_subs_raw.items():
            sub_id = sub_id_bytes.decode('utf-8')
            try:
                sub_data = json.loads(data_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                LOGGER.warning(f"Could not decode subscription {sub_id}, skipping")
                continue
            topic = sub_data.get('topic')
            if not topic:
                LOGGER.warning(f"Subscription {sub_id} has no topic, skipping")
                continue
            by_topic.setdefault(topic, {})[sub_id] = {
                'id': sub_id,
                'save_path': sub_data.get('save_path'),
                'filter': sub_data.get('filter', {}),
            }

        for topic, subscriptions in by_topic.items():
            mqtt_subscriber.subscribe(topic, subscriptions)
            LOGGER.info(
                f"Restored subscription: {topic} "
                f"({len(subscriptions)} subscription(s))")

    except Exception as e:
        LOGGER.error(f"Failed to load persisted subscriptions: {e}")


def run_manager():

    try:
        _host = os.getenv("GLOBAL_BROKER_HOST")
        _port = int(os.getenv("GLOBAL_BROKER_PORT", 443))
        _uid = os.getenv("GLOBAL_BROKER_USERNAME", "everyone")
        _pwd = os.getenv("GLOBAL_BROKER_PASSWORD", "everyone")
        _protocol = os.getenv("MQTT_PROTOCOL", "websockets")
        _session = os.getenv("MQTT_SESSION_ID", str(uuid4()))

    except Exception as e:
        LOGGER.error(f"Error setting global broker MQTT configuration: {e}")
        raise e

    broker_config = {
        'host': _host,
        'port': _port,
        'uid': _uid,
        'pwd': _pwd,
        'protocol': _protocol,
        'session': _session
    }

    subscriber_id = broker_config.get('host', 'unknown').replace('.', '-')
    health_key = f"subscriber:health:{subscriber_id}"

    if not broker_config.get('host'):
        LOGGER.error("No broker host provided, exiting")
        sys.exit(1)

    mqtt_subscriber = Subscriber(**broker_config)

    redis_listener = CommandListener(
        subscriber=mqtt_subscriber,
        channel=COMMAND_CHANNEL
    )
    redis_client = get_redis_client()

    mqtt_thread = threading.Thread(target=mqtt_subscriber.start, daemon=True)

    shutdown_event = threading.Event()

    def handle_shutdown(signum, frame):
        LOGGER.info("Received shutdown signal, shutting down")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    mqtt_thread.start()
    redis_listener.start()

    # get existing subscriptions from Redis and subscribe
    load_persisted_subscriptions(redis_client, mqtt_subscriber)

    LOGGER.info(f"Subscription manager started for broker: {broker_config.get('host')}")

    try:
        while not shutdown_event.is_set():
            time.sleep(1)
            redis_client.set(health_key, 'alive', ex=60)
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
