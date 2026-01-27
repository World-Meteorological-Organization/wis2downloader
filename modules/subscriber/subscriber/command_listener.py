import threading
import json
import time
import logging
import os

import redis
from shared import get_redis_client


LOGGER = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
LOGGER.setLevel(LOG_LEVEL)


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
                LOGGER.error(f'Redis connection error {e}. Retrying in 5 seconds')
                time.sleep(5)
            except Exception as e:
                LOGGER.error(f"Unexpected error {e} in CommandListener")

    def _process_command(self, message):
        try:
            command = json.loads(message['data'])
            action = command.get('action')
            topic = command.get('topic')
            save_path = command.get('save_path')
            if not all([action, topic]):
                LOGGER.warning(f'Invalid command received: {command}')
                return

            if action == 'subscribe':
                self.subscriber.subscribe(topic, save_path)
                LOGGER.info(f'Subscribed to new topic: {topic}, save path = {save_path}')
            elif action == 'unsubscribe':
                self.subscriber.unsubscribe(topic)
                LOGGER.info(f'Unsubscribed from {topic}')
            else:
                LOGGER.warning(f'Unknown action: {action}')

        except json.JSONDecodeError as e:
            LOGGER.error(f'Failed to decode command: {message}')
        except Exception as e:
            LOGGER.error(f'Unexpected error: {e}')

    def stop(self):
        self.stop_event.set()
        self.pubsub.unsubscribe(self.channel)
