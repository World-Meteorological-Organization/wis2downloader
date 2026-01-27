import json
import logging
import os
from pathlib import Path
from urllib.parse import unquote
import yaml
import time
from flask import Flask, request, jsonify, url_for, Response, render_template
from prometheus_client import generate_latest, REGISTRY, CollectorRegistry, \
    multiprocess
from prometheus_client import Counter, Gauge
from task_manager.worker import app as celery_app
import sys
from flask_cors import CORS
from redis.exceptions import ConnectionError

# Import shared Redis client
from shared import get_redis_client

# Import config loader from package
from . import load_config


# set up logging
log_formatter = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03dZ, %(name)s, %(levelname)s, %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
log_formatter.converter = time.gmtime

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG").upper())

# Clear existing handlers and add our stream handler
if root_logger.hasHandlers():
    root_logger.handlers.clear()
root_logger.addHandler(stream_handler)

LOGGER = logging.getLogger(__name__)

DATA_DIRECTORY = Path(
    os.getenv("DATA_BASEPATH", "/data/wis2-downloads")).resolve()


def get_json() -> dict:
    """Get JSON body safely."""
    if not request.is_json:
        return {}
    return request.get_json(silent=True) or {}


def normalise_topic(value: str | None) -> str | None:
    """Normalise/validate topic values from request path or payload."""
    if value is None:
        return None
    value = unquote(value).strip()
    return value or None


def normalise_path(userpath: str) -> str | None:
    if not userpath:
        return None

    resolved_path = (DATA_DIRECTORY / userpath).resolve()

    if (DATA_DIRECTORY not in resolved_path.parents and
            resolved_path != DATA_DIRECTORY):
        return None

    return str(resolved_path.relative_to(DATA_DIRECTORY))

# Load config
CONFIG = load_config()

# Redis pub/sub channel for subscription commands
COMMAND_CHANNEL = "subscription_commands"

# Now set up flask app
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev')
if FLASK_SECRET_KEY == 'dev':
    LOGGER.warning("Using insecure secret key for flask app")
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(SECRET_KEY=FLASK_SECRET_KEY)

# Redis key for storing subscriptions
GLOBAL_SUBSCRIPTION_KEY = "global:all_subscriptions"



def publish_command(command, channel):
    try:
        redis_client = get_redis_client()
        redis_client.publish(channel, json.dumps(command))
        LOGGER.info(f"Published command to {channel}: {command}")
        return True
    except ConnectionError as e:
        LOGGER.error(f"Failed to publish command to Redis: {e}")
        return False
    except Exception as e:
        LOGGER.error(f"Unexpected error: {e}")
        return False

def persist_subscription(topic, save_path, filters):
    try:
        redis_client = get_redis_client()
        data_to_persist = {
            "topic": topic,
            "save_path": save_path,
            "filters": filters
        }
        redis_client.hset(GLOBAL_SUBSCRIPTION_KEY, topic, json.dumps(data_to_persist))
        LOGGER.info(f"Persisted subscription for topic {topic}")
        return True

    except ConnectionError as e:
        LOGGER.error(f"Failed to persist subscriptions to Redis: {e}")
        return False

    except Exception as e:
        LOGGER.error(f"Unexpected error: {e}")
        return False


CELERY_DEFAULT_QUEUE = os.getenv("CELERY_DEFAULT_QUEUE", "celery")
CELERY_QUEUE_LENGTH = Gauge(
    'celery_queue_length_total',
    'Current number of tasks in the Celery default queue.',
    ['queue_name']  # Using a label in case you want to monitor multiple queues
)


# preload openapi doc
def load_openapi():
    p = Path(app.root_path) / 'static' / 'openapi.yml'
    if p.exists():
        with open(p) as fh:
            return yaml.safe_load(fh)
    else:
        return {}


OPENAPI = load_openapi()


# Define routes for subscription manager
# GET list of subscriptions
@app.route('/subscriptions')
def list_subscriptions():
    subscriptions = {}
    try:
        redis_client = get_redis_client()
        all_topics_bytes = redis_client.hgetall(GLOBAL_SUBSCRIPTION_KEY)
        if not all_topics_bytes:
            return jsonify(subscriptions), 200

        for topic_bytes, data_bytes in all_topics_bytes.items():
            topic = topic_bytes.decode('utf-8')
            try:
                details = json.loads(data_bytes.decode('utf-8'))
                subscriptions[topic] = details

            except json.JSONDecodeError:
                LOGGER.warning(f"Failed to decode subscription for topic {topic}")
                continue

    except ConnectionError as e:
        return jsonify({"error": f"Failed to connect to Redis: {e}"}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


    return jsonify(subscriptions), 200


# POST (add) new subscription
@app.post('/subscriptions')
def add_subscription():
    data = get_json()

    # Get and validate topic
    topic = normalise_topic(data.get('topic'))
    if topic is None:
        return jsonify({"error": "No topic provided"}), 400

    # Get location (target) where we want to save the data for this topic
    target = normalise_path(data.get('target', ''))

    command = {
        "action": "subscribe",
        "topic": topic,
        "save_path": target,
        "filters": []
    }

    # Publish command to subscriber via Redis
    if not publish_command(command, COMMAND_CHANNEL):
        return jsonify({"error": "Failed to queue subscription command, Redis service unavailable"}), 503

    # Persist subscription to Redis
    if not persist_subscription(topic, target, command.get("filters")):
        return jsonify({"error": "Failed to persist subscription to redis"}), 503

    # Create response
    response = jsonify({"status": "accepted", "topic": topic, "target": target})
    response.status_code = 202
    response.headers['Location'] = url_for('get_subscription', topic=topic)
    return response


# GET information on subscription
@app.get('/subscriptions/<path:topic>')
def get_subscription(topic):
    topic = unquote(topic)
    if not topic:
        return jsonify({"error": "No topic passed"}), 400
    try:
        redis_client = get_redis_client()
        subscription_data = redis_client.hget(GLOBAL_SUBSCRIPTION_KEY, topic)
        if subscription_data is None:
            return jsonify({"error": f"Subscription for topic {topic} not found"}), 404

        subscription_data = json.loads(subscription_data)
        return jsonify(subscription_data), 200

    except ConnectionError as e:
        return jsonify({"error": f"Failed to connect to Redis: {e}"}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


# DELETE subscription
@app.delete('/subscriptions/<path:topic>')
def delete_subscription(topic):
    topic = unquote(topic)
    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    # Publish unsubscribe command to subscriber via Redis
    command = {"action": "unsubscribe", "topic": topic}
    if not publish_command(command, COMMAND_CHANNEL):
        return jsonify({"error": "Failed to queue unsubscribe command"}), 503

    # Remove subscription from Redis
    try:
        redis_client = get_redis_client()
        redis_client.hdel(GLOBAL_SUBSCRIPTION_KEY, topic)
        LOGGER.info(f"Removed subscription: {topic}")
    except Exception as e:
        LOGGER.error(f"Failed to remove subscription from Redis: {e}")
        return jsonify({"error": "Failed to remove subscription"}), 503

    return jsonify({"status": "deleted", "topic": topic}), 200


# Swagger end point
@app.route('/')
@app.route('/swagger')
def render_swagger():
    return render_template('swagger.html', )


# Openapi doc endpoint
@app.route('/openapi')
def fetch_openapi():
    return jsonify(OPENAPI)


@app.route('/metrics')
def expose_metrics():
    """
    Expose the Prometheus metrics to be scraped.
    """

    redis_client = get_redis_client()
    try:
        # Use the Sentinel-aware redis_client to check queue length
        queue_length = redis_client.llen(CELERY_DEFAULT_QUEUE)
        CELERY_QUEUE_LENGTH.labels(queue_name=CELERY_DEFAULT_QUEUE).set(
            queue_length)
        registry = CollectorRegistry()
        basedir = os.getenv('PROMETHEUS_MULTIPROC_DIR',
                            '/tmp/prometheus_metrics')
        multiprocess.MultiProcessCollector(registry, path=basedir)

        # ToDo fix aggregation below

        # iterate over subdirectories
        for subdir in os.listdir(basedir):
            if os.path.isdir(os.path.join(basedir, subdir)):
                worker_path = os.path.join(basedir, subdir)
                multiprocess.MultiProcessCollector(registry, path=worker_path)

        return Response(generate_latest(registry), mimetype="text/plain")

    except Exception as e:
        LOGGER.error(
            f"Failed to generate metrics: {e}. Check Sentinel connection.")
        error_message = "Error generating metrics"
        return Response(error_message, status=500, mimetype="text/plain")


# health check end point
@app.route('/health')
def health_check():
    # Health check that pings the Sentinel-aware Redis client
    try:
        get_redis_client().ping()
        status = 'healthy'
    except Exception as e:
        LOGGER.error(f"Redis Sentinel connection failed for health check: {e}")
        status = 'unhealthy'

    return Response(response=json.dumps({'status': status}), status=200,
                    mimetype="application/json")


def run():
    app.run(debug=True, host=CONFIG['flask_host'],
            port=CONFIG['flask_port'], use_reloader=False)
