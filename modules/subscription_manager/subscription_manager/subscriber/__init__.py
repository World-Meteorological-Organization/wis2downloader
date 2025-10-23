import time
from datetime import datetime
from fnmatch import fnmatch
import json
import logging
import os
import ssl

import paho.mqtt.client as mqtt

from task_manager.workflows import wis2_download

LOGGER = logging.getLogger(__name__)

LOG_LEVEL = os.getenv("LOG_LEVEL","DEBUG").upper()
LOGGER.setLevel(LOG_LEVEL)

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
            self.client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                                cert_reqs=ssl.CERT_REQUIRED,
                                tls_version=ssl.PROTOCOL_TLS,
                                ciphers=None)
        self.client.username_pw_set(uid, pwd)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.active_subscriptions = {}
        self.retry_sleep = 1
        self.host = host
        self.port = port

        LOGGER.info(f"Connecting (Host: {host}, port: {port}, session: {session}) ...")

        try:
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
        target = self.active_subscriptions.get(msg.topic,{}).get('target')

        if target is None:
            for key, value in self.active_subscriptions.items():
                if fnmatch(msg.topic, value['pattern']):
                    target = value['target']
                    break

        if target is None:
            LOGGER.warning(f"Message received on {msg.topic} but unable to match target, skipping")
            return

        # ToDo - add in simple / quick filters here? or offload to celery?

        job = {
            "topic": msg.topic,
            "target": target,
            "_broker": self.host,
            "_received": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            '_queued': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            job['payload'] = json.loads(msg.payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to decode message payload: {e}")
            return

        workflow = wis2_download(job)
        workflow.apply_async()

    def subscribe(self, topic, target):
        self.client.subscribe(topic, qos=0)
        self.active_subscriptions[topic] = {
            'target': target,
            'pattern': topic.replace("+", "*").replace("#", "*")
        }
        LOGGER.info(f"Subscribed to {topic} on {self.host}")
        return self.active_subscriptions

    def unsubscribe(self, topic):
        if topic in self.active_subscriptions:
            self.client.unsubscribe(topic)
            del self.active_subscriptions[topic]
            LOGGER.info(f"Unsubscribed from {topic}")
        else:
            LOGGER.warning(f"subscription for topic {topic} not found")
        return self.active_subscriptions

    def start(self):
        self.client.loop_forever()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()