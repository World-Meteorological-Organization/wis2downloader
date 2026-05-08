import threading
import json
import time
from typing import TYPE_CHECKING

import redis
from shared import get_redis_client, setup_logging

if TYPE_CHECKING:
    from .subscriber import Subscriber

LOGGER = setup_logging(__name__)


class CommandListener(threading.Thread):
    def __init__(self, subscriber: 'Subscriber',
                 channel: str = 'subscription_commands'):
        # initialise thread as daemon
        super().__init__(daemon=True)
        self.subscriber = subscriber
        self.redis = get_redis_client()
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        self.channel = channel
        self.stop_event = threading.Event()
        LOGGER.info(f"Redis listener initialised for channel: {channel}")

    def _reconnect(self):
        """Recreate pubsub and resubscribe after connection failure."""
        try:
            self.pubsub.close()
        except Exception:
            pass
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        self.pubsub.subscribe(self.channel)
        LOGGER.info(f"Reconnected and resubscribed to channel: {self.channel}")

    def run(self):
        try:
            self.pubsub.subscribe(self.channel)
            LOGGER.info(f"Subscribed to channel: {self.channel}")
        except Exception as e:
            LOGGER.error(f"{e}")
            return

        while not self.stop_event.is_set():
            try:
                message = self.pubsub.get_message()
                if message and message['data'] != 1 and message['type'] == 'message':
                    self._process_command(message)
                time.sleep(1)
            except redis.exceptions.ConnectionError as e:
                LOGGER.error(f'Redis connection error {e}. Reconnecting in 5 seconds')
                time.sleep(5)
                try:
                    self._reconnect()
                except Exception as reconnect_error:
                    LOGGER.error(f'Reconnection failed: {reconnect_error}')
            except Exception as e:
                LOGGER.error(f"Unexpected error {e} in CommandListener")

    def _process_command(self, message):
        try:
            command = json.loads(message['data'])
            action = command.get('action')
            topic = command.get('topic')

            if not all([action, topic]):
                LOGGER.warning(f'Invalid command received: {command}')
                return

            if action == 'subscribe':
                subscriptions = command.get('subscriptions', {})
                self.subscriber.subscribe(topic, subscriptions)
                LOGGER.info(
                    f"Subscribed to topic: {topic} "
                    f"({len(subscriptions)} subscription(s))")

            elif action == 'unsubscribe':
                self.subscriber.unsubscribe(topic)
                LOGGER.info(f'Unsubscribed from {topic}')

            elif action == 'add_subscription':
                sub_id = command.get('sub_id')
                if not sub_id:
                    LOGGER.warning(f'add_subscription missing sub_id: {command}')
                    return
                self.subscriber.add_subscription(
                    topic,
                    sub_id,
                    command.get('save_path', ''),
                    command.get('filter', {}),
                    command.get('credentials'),
                )
                LOGGER.info(f'Added subscription {sub_id} to topic {topic}')

            elif action == 'remove_subscription':
                sub_id = command.get('sub_id')
                if not sub_id:
                    LOGGER.warning(f'remove_subscription missing sub_id: {command}')
                    return
                self.subscriber.remove_subscription(topic, sub_id)
                LOGGER.info(f'Removed subscription {sub_id} from topic {topic}')

            elif action == 'update_subscription':
                sub_id = command.get('sub_id')
                if not sub_id:
                    LOGGER.warning(f'update_subscription missing sub_id: {command}')
                    return
                # update is an upsert
                self.subscriber.add_subscription(
                    topic,
                    sub_id,
                    command.get('save_path', ''),
                    command.get('filter', {}),
                    command.get('credentials'),
                )
                LOGGER.info(f'Updated subscription {sub_id} on topic {topic}')

            else:
                LOGGER.warning(f'Unknown action: {action}')

        except json.JSONDecodeError:
            LOGGER.error(f'Failed to decode command: {message}')
        except Exception as e:
            LOGGER.error(f'Unexpected error: {e}')

    def stop(self):
        self.stop_event.set()
        self.pubsub.unsubscribe(self.channel)
