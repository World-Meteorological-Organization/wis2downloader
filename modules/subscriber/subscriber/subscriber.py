import certifi
from datetime import datetime, timezone
from fnmatch import fnmatch
import json
import paho.mqtt.client as mqtt
import ssl

from shared import setup_logging, incr_counter, DEFAULT_QUEUE
from task_manager.workflows import wis2_download


LOGGER = setup_logging(__name__)


class Subscriber():
    def __init__(self, host: str = "globalbroker.meteo.fr",
                 port: int = 443, uid: str = "everyone",
                 pwd: str = "everyone", protocol: str = "websockets",
                 session: str = '', queue_delay: int = 0):

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
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe

        # {topic: {'pattern': str, 'subscriptions': {sub_id: {'id', 'save_path', 'filter'}}}}
        self.active_subscriptions = {}
        self.host = host
        self.port = port
        # Seconds to hold jobs from a non-preferred broker so the preferred copy wins dedup
        self.queue_delay = queue_delay

        LOGGER.info(f"Connecting (Host: {host}, port: {port}, session: {session}) ...")

        try:
            LOGGER.warning(f"Connecting to {host}:{port}")
            self.client.connect(host, port)
        except Exception as e:
            LOGGER.error(f"Failed to connect to {host}: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            LOGGER.error(f"Connection to {self.host} failed: {reason_code}")
            return
        LOGGER.info(f"Connected to {self.host} (session present: {flags.session_present})")
        # The broker may have dropped our session while we were disconnected
        topics = list(self.active_subscriptions)
        for topic in topics:
            client.subscribe(topic, qos=0)
        if topics:
            LOGGER.info(f"Resubscribed to {len(topics)} topic(s) on {self.host}")

    def _on_connect_fail(self, client, userdata):
        LOGGER.warning(f"Reconnect to {self.host} failed, retrying")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code,
                       properties):
        if reason_code == 0:
            LOGGER.info("Disconnected successfully")
        elif reason_code > 0:
            LOGGER.error(f"Disconnected from {self.host}: {reason_code}")

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        for sub_result in reason_codes:
            if sub_result in [0, 1, 2]:
                LOGGER.info("Subscription to topic successful")
            elif sub_result >= 128:
                LOGGER.error(
                    f"Subscription to topic failed with error code {sub_result}")

    def _on_message(self, client, userdata, msg):
        LOGGER.info(f"Message received on topic {msg.topic}")

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
            LOGGER.warning(
                f"Message received on {msg.topic} but no subscriptions configured, skipping")
            return

        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to decode message payload: {e}")
            return

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        incr_counter('notifications_received_total', {'broker': self.host})
        for sub_data in subscriptions.values():
            job = {
                "topic": msg.topic,
                "target": sub_data.get('save_path', ''),
                "filter": sub_data.get('filter', {}),
                "credentials": sub_data.get('credentials'),
                "_broker": self.host,
                "_received": now,
                "_queued": now,
                "payload": payload,
            }
            try:
                queue = sub_data.get('queue', DEFAULT_QUEUE)
                wis2_download(job, queue=queue).apply_async(countdown=self.queue_delay or None)
                LOGGER.info(
                    f"Job queued for topic {msg.topic} "
                    f"on queue '{queue}'"
                )
            except Exception as e:
                LOGGER.error(
                    f"Failed to queue job for topic {msg.topic}: {e}",
                    exc_info=True)
                incr_counter('queue_errors_total', {'broker': self.host})

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
                         save_path: str, filter_config: dict,
                         credentials: dict | None = None,
                         queue: str = DEFAULT_QUEUE) -> bool:
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
            'credentials': credentials,
            'queue': queue,
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
