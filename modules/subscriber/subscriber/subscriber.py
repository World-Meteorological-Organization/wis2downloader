import certifi
from datetime import datetime
from fnmatch import fnmatch
import json
import paho.mqtt.client as mqtt
import ssl
import time

from shared.logging import setup_logging
from task_manager.workflows import wis2_download


LOGGER = setup_logging(__name__)


class Subscriber():
    def __init__(self, host: str = "globalbroker.meteo.fr",
                 port: int = 443, uid: str = "everyone",
                 pwd: str = "everyone", protocol: str = "websockets",
                 session: str = ''):

        args = {
            'callback_api_version': mqtt.CallbackAPIVersion.VERSION2,
            'transport': protocol,
        }

        if len(session) > 0:
            args['client_id'] = session
            args['clean_session'] = False

        self.client = mqtt.Client(**args)

        if port in [443, 8883]:
            self.client.tls_set(ca_certs=certifi.where(),
                                certfile=None,
                                keyfile=None,
                                cert_reqs=ssl.CERT_REQUIRED,
                                tls_version=ssl.PROTOCOL_TLS,
                                ciphers=None)
        self.client.username_pw_set(uid, pwd)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe

        # {topic: {'pattern': str, 'subscriptions': {sub_id: {'id', 'save_path', 'filter'}}}}
        self.active_subscriptions = {}
        self.retry_sleep = 1
        self.host = host
        self.port = port

        LOGGER.info(f"Connecting (Host: {host}, port: {port}, session: {session}) ...")

        try:
            LOGGER.warning(f"Connecting to {host}:{port}")
            self.client.connect(host, port)
        except Exception as e:
            LOGGER.error(f"Failed to connect to {host}: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            LOGGER.info("Connected successfully")
        elif reason_code > 0:
            LOGGER.error(f"Connection failed with error code {reason_code}")
        self.retry_sleep = 1

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code,
                       properties):
        if reason_code == 0:
            LOGGER.info("Disconnected successfully")
        elif reason_code > 0:
            LOGGER.error(f"Disconnection to {self.host} failed with error code {reason_code}")
            time.sleep(self.retry_sleep)
            self.retry_sleep = min(self.retry_sleep*2, 360)

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        for sub_result in reason_codes:
            if sub_result in [0, 1, 2]:
                LOGGER.info("Subscription to topic successful")
            elif sub_result >= 128:
                LOGGER.error(
                    f"Subscription to topic failed with error code {sub_result}")

    def _on_message(self, client, userdata, msg):
        LOGGER.debug(f"Message received on topic {msg.topic}")

        # Find the matching subscription entry (exact match first, then glob)
        sub = self.active_subscriptions.get(msg.topic)
        if sub is None:
            for value in list(self.active_subscriptions.values()):
                if fnmatch(msg.topic, value['pattern']):
                    sub = value
                    break

        if sub is None:
            LOGGER.warning(
                f"Message received on {msg.topic} but no matching subscription, skipping")
            return

        subscriptions = sub.get('subscriptions', {})
        if not subscriptions:
            LOGGER.debug(
                f"Message received on {msg.topic} but no subscriptions configured, skipping")
            return

        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to decode message payload: {e}")
            return

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        for sub_data in subscriptions.values():
            job = {
                "topic": msg.topic,
                "target": sub_data.get('save_path', ''),
                "filter": sub_data.get('filter', {}),
                "_broker": self.host,
                "_received": now,
                "_queued": now,
                "payload": payload,
            }
            wis2_download(job).apply_async()

    def subscribe(self, topic: str, subscriptions: dict) -> dict:
        """Subscribe to an MQTT topic with an initial set of subscriptions.

        If the topic is already subscribed, the subscriptions dict replaces
        the existing one (upsert). The MQTT subscription is only issued once.

        subscriptions: {sub_id: {'id': str, 'save_path': str, 'filter': dict}}
        """
        if topic not in self.active_subscriptions:
            self.client.subscribe(topic, qos=0)
            LOGGER.info(f"Subscribed to {topic} on {self.host}")

        self.active_subscriptions[topic] = {
            'pattern': topic.replace("+", "*").replace("#", "*"),
            'subscriptions': dict(subscriptions),
        }
        LOGGER.info(
            f"Topic {topic} configured with {len(subscriptions)} subscription(s)")
        return self.active_subscriptions

    def add_subscription(self, topic: str, sub_id: str,
                         save_path: str, filter_config: dict) -> bool:
        """Add or update a single subscription on an already-subscribed topic.

        Returns True on success, False if the topic is not currently subscribed.
        """
        if topic not in self.active_subscriptions:
            LOGGER.warning(
                f"Cannot add subscription: topic '{topic}' not subscribed")
            return False
        self.active_subscriptions[topic]['subscriptions'][sub_id] = {
            'id': sub_id,
            'save_path': save_path,
            'filter': filter_config,
        }
        LOGGER.info(f"Added subscription {sub_id} to topic {topic}")
        return True

    def remove_subscription(self, topic: str, sub_id: str) -> bool:
        """Remove a subscription from a topic.

        Does not affect the MQTT subscription — call unsubscribe() explicitly
        when the last subscription for a topic is removed.
        Returns True on success, False if the topic is not subscribed.
        """
        if topic not in self.active_subscriptions:
            LOGGER.warning(
                f"Cannot remove subscription: topic '{topic}' not subscribed")
            return False
        sub = self.active_subscriptions[topic]
        if sub['subscriptions'].pop(sub_id, None) is None:
            LOGGER.warning(
                f"Subscription {sub_id} not found on topic {topic}")
        LOGGER.info(f"Removed subscription {sub_id} from topic {topic}")
        return True

    def unsubscribe(self, topic: str) -> dict:
        """Remove a topic subscription and all its subscriptions."""
        if topic in self.active_subscriptions:
            self.client.unsubscribe(topic)
            del self.active_subscriptions[topic]
            LOGGER.info(f"Unsubscribed from {topic}")
        else:
            LOGGER.warning(f"Subscription for topic '{topic}' not found")
        return self.active_subscriptions

    def start(self):
        self.client.loop_forever()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
