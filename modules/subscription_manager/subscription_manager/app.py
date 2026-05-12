import json
import os
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4
import yaml
from flask import Flask, request, jsonify, url_for, Response, render_template
from redis.exceptions import ConnectionError

from shared import get_redis_client, setup_logging, set_gauge, generate_prometheus_text

# Set up logging
setup_logging()  # Configure root logger
LOGGER = setup_logging(__name__)

DATA_DIRECTORY = Path(
    os.getenv("CONTAINER_DATA_PATH", "/data")).resolve()

try:
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
except Exception as e:
    LOGGER.error(f"Error getting flask host and port: {e}")
    raise e


VALID_CRED_TYPES = {"basic", "bearer"}
VALID_QUEUES = {"high_priority", "small_files", "large_files"}
DEFAULT_QUEUE = "small_files"


def _validate_credentials(creds: dict | None) -> dict | None:
    if creds is None:
        return None
    if not isinstance(creds, dict):
        raise ValueError("credentials must be an object")
    if creds.get("type") not in VALID_CRED_TYPES:
        raise ValueError("credentials.type must be 'basic' or 'bearer'")
    if creds["type"] == "basic" and not (creds.get("username") and creds.get("password")):
        raise ValueError("basic auth requires username and password")
    if creds["type"] == "bearer" and not creds.get("token"):
        raise ValueError("bearer auth requires token")
    return creds


def _redact_credentials(sub_data: dict) -> dict:
    safe = dict(sub_data)
    creds = safe.get("credentials")
    if creds:
        safe["credentials"] = {
            "type": creds.get("type"),
            **({"username": creds["username"]} if creds.get("username") else {}),
        }
    return safe


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


# Redis pub/sub channel for subscription commands
COMMAND_CHANNEL = "subscription_commands"

# Redis key — flat hash: sub_id → JSON({id, topic, save_path, filter})
GLOBAL_SUBSCRIPTIONS_KEY = "global:subscriptions"

# Flask app
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
if not FLASK_SECRET_KEY:
    raise ValueError("FLASK_SECRET_KEY must be set")
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(SECRET_KEY=FLASK_SECRET_KEY)


# ==================== REDIS HELPERS ====================

def publish_command(command: dict) -> bool:
    try:
        redis_client = get_redis_client()
        redis_client.publish(COMMAND_CHANNEL, json.dumps(command))
        LOGGER.info(f"Published command: {command}")
        return True
    except ConnectionError as e:
        LOGGER.error(f"Failed to publish command to Redis: {e}")
        return False
    except Exception as e:
        LOGGER.error(f"Unexpected error publishing command: {e}")
        return False


def _get_all_subscriptions() -> dict:
    """Read all subscriptions from Redis. Returns {sub_id: sub_data}."""
    redis_client = get_redis_client()
    raw = redis_client.hgetall(GLOBAL_SUBSCRIPTIONS_KEY)
    result = {}
    for k, v in raw.items():
        sub_id = k.decode('utf-8')
        try:
            result[sub_id] = json.loads(v.decode('utf-8'))
        except json.JSONDecodeError:
            LOGGER.warning(f"Could not decode subscription {sub_id}")
    return result


def _get_subscription(sub_id: str) -> dict | None:
    """Read a single subscription. Returns None if not found."""
    try:
        redis_client = get_redis_client()
        raw = redis_client.hget(GLOBAL_SUBSCRIPTIONS_KEY, sub_id)
        if raw is None:
            return None
        return json.loads(raw.decode('utf-8'))
    except Exception as e:
        LOGGER.error(f"Error reading subscription '{sub_id}': {e}")
        return None


def _persist_subscription(sub_id: str, sub_data: dict) -> bool:
    try:
        redis_client = get_redis_client()
        redis_client.hset(GLOBAL_SUBSCRIPTIONS_KEY, sub_id, json.dumps(sub_data))
        return True
    except Exception as e:
        LOGGER.error(f"Error persisting subscription '{sub_id}': {e}")
        return False


def _delete_subscription(sub_id: str) -> bool:
    try:
        redis_client = get_redis_client()
        redis_client.hdel(GLOBAL_SUBSCRIPTIONS_KEY, sub_id)
        return True
    except Exception as e:
        LOGGER.error(f"Error deleting subscription '{sub_id}': {e}")
        return False


def _subs_for_topic(topic: str, all_subs: dict) -> dict:
    """Return {sub_id: sub_data} for all subscriptions matching a topic."""
    return {k: v for k, v in all_subs.items() if v.get('topic') == topic}


def _group_by_topic(all_subs: dict) -> dict:
    """Group flat {sub_id: sub_data} into {topic: {sub_id: {save_path, filter}}}."""
    grouped: dict[str, dict] = {}
    for sub_id, sub_data in all_subs.items():
        topic = sub_data.get('topic')
        if not topic:
            continue
        grouped.setdefault(topic, {})[sub_id] = {
            'save_path': sub_data.get('save_path'),
            'filter': sub_data.get('filter', {}),
        }
    return grouped


CELERY_DEFAULT_QUEUE = os.getenv("CELERY_DEFAULT_QUEUE", "celery")


# preload openapi doc
def load_openapi():
    p = Path(app.root_path) / 'static' / 'openapi.yml'
    if p.exists():
        with open(p) as fh:
            return yaml.safe_load(fh)
    else:
        return {}


OPENAPI = load_openapi()


# ==================== SUBSCRIPTIONS ====================

@app.get('/subscriptions')
def list_subscriptions():
    """List all subscriptions grouped by topic.

    Returns: {topic: {sub_id: {save_path, filter}}}
    """
    try:
        return jsonify(_group_by_topic(_get_all_subscriptions())), 200
    except ConnectionError as e:
        return jsonify({"error": f"Failed to connect to Redis: {e}"}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


@app.post('/subscriptions')
def add_subscription():
    """Create a new subscription. Assigns a UUID and returns the full subscription."""
    data = get_json()

    topic = normalise_topic(data.get('topic'))
    if topic is None:
        return jsonify({"error": "No topic provided"}), 400

    save_path = normalise_path(data.get('target', '') or '')
    # accept both 'filter' (new) and 'filters' (legacy) in the request body
    filter_config = data.get('filter') or data.get('filters') or {}

    try:
        credentials = _validate_credentials(data.get('credentials'))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    queue = data.get('queue', DEFAULT_QUEUE)
    if queue not in VALID_QUEUES:
        return jsonify({
            "error": f"queue must be one of: {', '.join(sorted(VALID_QUEUES))}"
        }), 400

    sub_id = str(uuid4())
    sub_data = {
        'id': sub_id,
        'topic': topic,
        'save_path': save_path,
        'filter': filter_config,
        'credentials': credentials,
        'queue': queue,
    }

    try:
        all_subs = _get_all_subscriptions()
    except ConnectionError as e:
        return jsonify({"error": f"Failed to connect to Redis: {e}"}), 503

    existing_for_topic = _subs_for_topic(topic, all_subs)
    is_new_topic = len(existing_for_topic) == 0

    if not _persist_subscription(sub_id, sub_data):
        return jsonify({"error": "Failed to persist subscription to Redis"}), 503

    if is_new_topic:
        # First subscription for this topic — create the MQTT subscription
        command = {
            "action": "subscribe",
            "topic": topic,
            "subscriptions": {
                sub_id: {
                    'id': sub_id,
                    'save_path': save_path,
                    'filter': filter_config,
                    'credentials': credentials,
                    'queue': queue,
                }
            },
        }
    else:
        # Topic already subscribed — register the new subscription
        command = {
            "action": "add_subscription",
            "topic": topic,
            "sub_id": sub_id,
            "save_path": save_path,
            "filter": filter_config,
            'credentials': credentials,
            'queue': queue,
        }

    if not publish_command(command):
        return jsonify({"error": "Failed to queue subscription command, Redis unavailable"}), 503

    response = jsonify(_redact_credentials(sub_data))
    response.status_code = 201
    response.headers['Location'] = url_for('get_subscription', sub_id=sub_id)
    return response


@app.get('/subscriptions/<sub_id>')
def get_subscription(sub_id):
    """Get details for a specific subscription."""
    sub_data = _get_subscription(sub_id)
    if sub_data is None:
        return jsonify({"error": f"Subscription '{sub_id}' not found"}), 404
    return jsonify(_redact_credentials(sub_data)), 200


@app.put('/subscriptions/<sub_id>')
def update_subscription(sub_id):
    """Update a subscription's save path or filter."""
    sub_data = _get_subscription(sub_id)
    if sub_data is None:
        return jsonify({"error": f"Subscription '{sub_id}' not found"}), 404

    data = get_json()
    if 'target' in data:
        sub_data['save_path'] = normalise_path(data['target'])
    if 'filter' in data:
        sub_data['filter'] = data['filter']
    if 'credentials' in data:
        try:
            sub_data['credentials'] = _validate_credentials(
                data['credentials'])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    if 'queue' in data:
        if data['queue'] not in VALID_QUEUES:
            return jsonify({
                "error": (
                    f"queue must be one of: "
                    f"{', '.join(sorted(VALID_QUEUES))}"
                )
            }), 400
        sub_data['queue'] = data['queue']

    if not _persist_subscription(sub_id, sub_data):
        return jsonify({"error": "Failed to persist update to Redis"}), 503

    command = {
        "action": "update_subscription",
        "topic": sub_data['topic'],
        "sub_id": sub_id,
        "save_path": sub_data['save_path'],
        "filter": sub_data['filter'],
        "credentials": sub_data.get('credentials'),
        "queue": sub_data.get('queue', DEFAULT_QUEUE),
    }
    if not publish_command(command):
        return jsonify({"error": "Failed to queue update command"}), 503

    return jsonify(_redact_credentials(sub_data)), 200


@app.delete('/subscriptions/<sub_id>')
def delete_subscription(sub_id):
    """Delete a subscription. Sends unsubscribe only when the last subscription for the topic is removed."""
    sub_data = _get_subscription(sub_id)
    if sub_data is None:
        return jsonify({"error": f"Subscription '{sub_id}' not found"}), 404

    topic = sub_data['topic']

    if not _delete_subscription(sub_id):
        return jsonify({"error": "Failed to delete subscription from Redis"}), 503

    try:
        remaining = _subs_for_topic(topic, _get_all_subscriptions())
    except ConnectionError as e:
        return jsonify({"error": f"Failed to connect to Redis: {e}"}), 503

    if len(remaining) == 0:
        # Last subscription for this topic — close the MQTT subscription
        command = {"action": "unsubscribe", "topic": topic}
    else:
        # Other subscriptions remain — just remove this one from the routing table
        command = {"action": "remove_subscription", "topic": topic, "sub_id": sub_id}

    if not publish_command(command):
        return jsonify({"error": "Failed to queue command"}), 503

    return jsonify({"status": "deleted", "id": sub_id}), 200


# ==================== MONITORING ====================

@app.route('/')
@app.route('/swagger')
def render_swagger():
    return render_template('swagger.html', )


@app.route('/openapi')
def fetch_openapi():
    return jsonify(OPENAPI)


@app.route('/metrics')
def expose_metrics():
    """Expose Prometheus metrics to be scraped."""
    try:
        redis_client = get_redis_client()
        queue_length = sum(
            redis_client.llen(q) for q in VALID_QUEUES
        )
        set_gauge(
            'celery_queue_length',
            {'queue_name': CELERY_DEFAULT_QUEUE},
            queue_length,
        )

        text = generate_prometheus_text()
        return Response(text, mimetype="text/plain")

    except Exception as e:
        LOGGER.error(f"Failed to generate metrics: {e}")
        return Response("Error generating metrics", status=500, mimetype="text/plain")


@app.route('/health')
def health_check():
    try:
        get_redis_client().ping()
        status = 'healthy'
    except Exception as e:
        LOGGER.error(f"Redis connection failed for health check: {e}")
        status = 'unhealthy'

    return Response(response=json.dumps({'status': status}), status=200,
                    mimetype="application/json")


def run():
    _debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=_debug, host=FLASK_HOST, port=FLASK_PORT, use_reloader=False)
