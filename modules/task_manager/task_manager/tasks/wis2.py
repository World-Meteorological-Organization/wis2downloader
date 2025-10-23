import base64
from celery import Task, current_task
from celery.utils.log import get_task_logger
import datetime as dt
from dateutil.relativedelta import relativedelta
from functools import wraps
import importlib
import json
import os
from pathlib import Path
from prometheus_client import Counter, Gauge
import redis
import time
import urllib3
from urllib.parse import urlsplit

from task_manager.worker import app as app

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_VALID_CONDITIONS = [STATUS_SUCCESS, STATUS_FAILED, STATUS_SKIPPED]
REDIS_TTL_SECONDS = int(os.getenv("REDIS_TTL_SECONDS", 3600))
LOCK_EXPIRE = int(os.getenv("REDIS_MESSAGE_LOCK", 300))

_pool = urllib3.PoolManager()
hash_module = importlib.import_module("hashlib")

# environment variables
DATA_BASEPATH = os.getenv("DATA","/data") # this needs checking
REDIS_HOST = os.getenv("REDIS_HOST","redis")
REDIS_PORT = os.getenv("REDIS_PORT","6379")

LOGGER = get_task_logger(__name__)

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

TRACKER = "wis2:notifications:data:tracker"


# define some metrics for prometheus

NOTIFICATIONS_RECEIVED = Counter(
    'notifications_received',
    'Total number of notifications received.',
    ['broker', 'cache', 'centre_id', 'topic']
)

NOTIFICATIONS_SKIPPED = Counter(
    'notifications_skipped',
    'Total number of notifications skipped.',
    ['broker', 'cache', 'centre_id', 'topic', 'reason']
)

DOWNLOADS_FAILED = Counter(
    'failed_downloads',
    'Total number of failed downloads.',
    ['cache', 'centre_id', 'topic', 'reason', 'file_type']
)


DOWNLOADS_TOTAL_FILES = Counter(
    'downloads_total_files',
    'Total number of files downloaded.',
    ['broker', 'cache', 'centre_id', 'topic', 'file_type']
)

DOWNLOADS_TOTAL_BYTES = Counter(
    'downloads_total_bytes',
    'Total number of bytes downloaded.',
    ['broker', 'cache', 'centre_id', 'topic', 'file_type']
)


def set_status(key, type, status):
    if key in (None, ''):
        LOGGER.error("No key provided")
        return
    if type not in ('by-msg-id', 'by-hash', 'by-data-id'):
        LOGGER.error(f"Invalid type {type}")
        return
    tracker_id = f"{TRACKER}:{type}:{key}"
    redis_client.hset(tracker_id, 'status', status)
    redis_client.expire(tracker_id, REDIS_TTL_SECONDS)  # Set expiration


def get_status(key, type):
    status = None
    if key in (None, ''):
        LOGGER.error("No key provided")
        return status
    if type not in ('by-msg-id', 'by-hash', 'by-data-id'):
        LOGGER.error(f"Invalid type {type}")
        return status

    tracker_id = f"{TRACKER}:{type}:{key}"
    if redis_client.hexists(tracker_id,'status'):
        status = redis_client.hget(tracker_id,'status')
        status = status.decode('utf-8')
        if status not in STATUS_VALID_CONDITIONS:
            LOGGER.warning(f"Invalid status '{status}' for {key}")

    return status


def _select_download_link(links):
    """
    Prefers 'update' (overwrite=True), otherwise 'canonical' (overwrite=False).
    Returns (download_url, expected_length, overwrite)
    """
    download_url = None
    expected_length = None
    overwrite = False
    for link in links:
        rel = link.get('rel')
        if rel == 'update':
            download_url = link.get('href')
            expected_length = link.get('length')
            overwrite = True
            break
        if rel == 'canonical' and download_url is None:
            download_url = link.get('href')
            expected_length = link.get('length')
    return download_url, expected_length, overwrite


def _now_utc_str() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def metrics_collector(func):
    # the download_from_wis function has several return points, hence, to
    # ensure we collect metrics each one wrap in a function. Previously, some
    # were missed or wrong.
    #
    # 1) Total number of notifications received, incl. split by cache, centre-id and topic
    # 2) Number of notifications skipped due to the data already successfully having been processed
    # 3) Number of downloads attempted
    # 4) Number of downloads successful
    # 5) Number of bytes downloaded

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        status_code = result.get('status','')
        global_cache = result.get('global_cache','')
        global_broker = result.get('broker','')
        topic = result.get('topic','')
        reason = result.get('reason','')
        error_class = result.get('error_class','')
        centre_id = result.get('centre_id','')
        file_size = result.get('actual_filesize',0)
        file_type = result.get('file_type','')

        try:

            NOTIFICATIONS_RECEIVED.labels(broker=global_broker,
                                          cache=global_cache,
                                          centre_id=centre_id,
                                          topic=topic).inc()
            # totals per broker
            NOTIFICATIONS_RECEIVED.labels(broker=global_broker,
                                          cache='total',
                                          centre_id=centre_id,
                                          topic='total').inc()

            if status_code == STATUS_SKIPPED:
                NOTIFICATIONS_SKIPPED.labels(broker=global_broker,
                                             cache=global_cache,
                                             centre_id=centre_id,
                                             topic=topic,
                                             reason=error_class).inc()

            if status_code == STATUS_FAILED:
                DOWNLOADS_FAILED.labels(
                    cache=global_cache,
                    centre_id=centre_id,
                    topic=topic,
                    file_type=file_type,
                    reason=error_class
                ).inc()

            if status_code == STATUS_SUCCESS:
                DOWNLOADS_TOTAL_FILES.labels(
                    broker=global_broker,
                    cache=global_cache,
                    centre_id=centre_id,
                    topic=topic,
                    file_type = file_type
                ).inc()

                DOWNLOADS_TOTAL_FILES.labels(
                    broker=global_broker,
                    cache=global_cache,
                    centre_id='total',
                    topic='total',
                    file_type = file_type
                ).inc()

                DOWNLOADS_TOTAL_BYTES.labels(
                    broker=global_broker,
                    cache=global_cache,
                    centre_id='total',
                    topic=topic,
                    file_type=file_type
                ).inc(file_size)


                DOWNLOADS_TOTAL_BYTES.labels(
                    broker=global_broker,
                    cache=global_cache,
                    centre_id='total',
                    topic='total',
                    file_type=file_type
                ).inc(file_size)
        except Exception as e:
            LOGGER.error(f"Error collecting metrics: {e}", exc_info=True)

        return result
    return wrapper


@app.task(bind=True)
@metrics_collector
def download_from_wis2(self, job):
    # set up return dict
    result = {
        'id': None,
        'data_id': None,
        'topic': None,
        'broker': None,
        'global_cache': None,
        'metadata_id': None,
        'received': None,
        'queued': None,
        'download_start': None,
        'download_end': None,
        'download_url': None,
        'processed': None,
        'status': None,
        'reason': None,
        'error_class': None,
        'filepath': None,
        'file_type': None,
        'save': False,
        'expected_hash': None,
        'actual_hash': None,
        'hash_method': None,
        'valid_hash': None,
        'expected_filesize': None,
        'actual_filesize': None
    }

    # get output directory
    target_directory = job.get("target","")

    # now get topic
    topic = job.get("topic")
    result['topic'] = topic

    if topic is None:
        result['status'] = STATUS_FAILED
        result['reason'] = "Notification message is missing 'topic'"
        result['error_class'] = "MissingTopicError"
        return result

    # decompose topic to get centre-id
    topic_parts = topic.split('/')
    centre_id = topic_parts[3] if len(topic_parts) > 3 and topic_parts[2] == 'wis2' else 'unknown'
    result['centre_id'] = centre_id

    file_type = 'unknown'
    result['file_type'] = file_type

    # get identifiers (incl. file hash if present)
    message_id = job.get('payload',{}).get('id')
    result['id'] = message_id

    data_id = job.get('payload',{}).get('properties',{}).get('data_id')
    result['data_id'] = data_id

    filehash = job.get('payload',{}).get('properties',{}).get('integrity',{}).get('value')  # noqa
    result['filehash'] = filehash

    metadata_id = job['payload']['properties'].get("metadata_id")
    result['metadata_id'] = metadata_id

    result['broker'] = job['_broker']
    result['received'] = job['_received']
    result['queued'] = job['_queued']

    # deduplication step
    for key, type in [(message_id, 'by-msg-id'), (data_id, 'by-data-id'), (filehash, 'by-hash')]:
        if key:
            status = get_status(key, type)
            if status and status == STATUS_SUCCESS:
                result['status'] = STATUS_SKIPPED
                result['reason'] = f"ID '{key}' ({type}) previously processed with status '{status}'"
                result['error_class'] = "PreviouslyProcessed"
                return result


    # !! ToDo - the logic here needs checking !!
    # acquire lock on ID to make sure we only process once.
    lock_key_identifier = filehash or data_id or message_id
    lock_key = f"wis2:notification:data:lock:{lock_key_identifier}"
    lock_acquired = redis_client.set(lock_key, 1, nx=True, ex=LOCK_EXPIRE)
    if not lock_acquired:  # lock acquired by another worker
        LOGGER.warning(f"Could not acquire lock for {lock_key_identifier}, retrying in 10 seconds")
        raise self.retry(countdown=10, max_retries=10)


    # At this point, we have not seen the ID before, and we have lock on ID.
    # Now attempt download
    try:
        # Now parse download URL from payload link
        download_url, expected_length, overwrite = _select_download_link(job['payload']['links'])
        result['download_url'] = download_url

        # get file_type from filename extension, this doesn't always work
        # hence later we also check the file header for GRIB or BUFR.
        if download_url:
            filename = os.path.basename(urlsplit(download_url).path)
            if '.' in filename:
                file_type = filename.split('.')[-1]
                result['file_type'] = file_type

        # check we have a download URL
        if not download_url:
            result['status'] = STATUS_FAILED
            result['reason'] = "No download URL in notification message"
            result['error_class'] = "MissingDownloadURLError"
            return result

        # prepare filepath
        today = dt.date.today()
        target_directory = Path(DATA_BASEPATH) / job.get("target", "") / f"{today:%Y/%m/%d}"
        target_directory.mkdir(exist_ok=True, parents=True)
        filename = os.path.basename(urlsplit(download_url).path)
        output_path = target_directory / filename
        result['filepath'] = str(output_path)
        
        # extract cache
        result['global_cache'] = urlsplit(download_url).hostname

        if result['global_cache'] in ("wis2.ncm.gov.sa"):
            result['status'] = STATUS_SKIPPED
            result['reason'] = "Global cache black listed, skipped"
            result['error_class'] = "GlobalCacheBlacklisted"
            LOGGER.warning(f"File {output_path} skipped from blacklisted cache")
            return result

        # check if the file exists, if so we have already processed this notification
        if output_path.exists() and not overwrite:
            result['status'] = STATUS_FAILED
            result['reason'] = "File already exists and overwrite is not requested"
            result['error_class'] = "FileExistsError"
            LOGGER.warning(f"File {output_path} already exists, skipping")
            return result

        # ToDo - investigate whether we want to replace the following with aria2
        # download the data
        result['download_start'] = _now_utc_str()
        try:
            response = _pool.request('GET', download_url,
                                 timeout=urllib3.Timeout(connect=5.0, read=60.0))
        except urllib3.exceptions.ConnectTimeoutError as e:
            result['status'] = STATUS_FAILED
            result['reason'] = f"Connection timeout error {e} for {result['global_cache']}"
            result['error_class'] = str(e.__class__.__name__)
        except urllib3.exceptions.ReadTimeoutError as e:
            result['status'] = STATUS_FAILED
            result['reason'] = f"Download timeout  error {e} for {result['global_cache']}"
            result['error_class'] = str(e.__class__.__name__)
        except urllib3.exceptions.MaxRetryError as e:
            result['status'] = STATUS_FAILED
            result['reason'] = f"Maximum retries downloading from {result['global_cache']} exceeded"
            result['error_class'] = str(e.__class__.__name__)
        except Exception as e:
            result['status'] = STATUS_FAILED
            result['reason'] = f"Error {e} while downloading from {result['global_cache']}"
            result['error_class'] = str(e.__class__.__name__)
        result['download_end'] = _now_utc_str()

        # verify and save the file
        data = response.data
        result['actual_filesize'] = len(data)

        # update filetype
        if len(data) >= 4:
            header = data[0:4].decode('utf-8', errors='ignore')
            if header == 'BUFR':
                file_type = 'bufr'
            elif header == 'GRIB': # GRIB is often represented by 'GRIB' or 'GRB'
                file_type = 'grib'

        if file_type == 'bufr4':  # chnage to bufr cor consistency
            file_type = 'bufr'

        result['file_type'] = file_type

        # hash verification
        hash_props = job['payload']['properties'].get('integrity',{})
        hash_method = hash_props.get('method','sha512')
        hash_expected = hash_props.get('value')

        if hash_method:
            sanitized_method = hash_method.replace('-', '_')
            hash_function = getattr(hash_module, sanitized_method, None)
            if not hash_function:
                LOGGER.error(f"Invalid hash method '{hash_method}'")
            else:
                hash_bytes = hash_function(data).digest()
                hash_base64 = base64.b64encode(hash_bytes).decode()
                result['hash_method'] = hash_method
                result['expected_hash'] = hash_expected
                result['actual_hash'] = hash_base64
                if hash_expected:
                    result['valid_hash'] = (hash_base64 == hash_expected)
                    if not result['valid_hash']:
                        LOGGER.error(f"Hash verification failed for {download_url}")
                        result['status'] = STATUS_FAILED
                        result['reason'] = f"Hash verification failed for {download_url}"
                        result['error_class'] = "HashVerificationError"
                        return result

        # now save the data
        output_path.write_bytes(data)
        result['save'] = True
        result['status'] = STATUS_SUCCESS

        # update metrics

        LOGGER.warning(result)
        return result

    except Exception as e:
        LOGGER.error(f"Error processing job {message_id}: {e}", exc_info=True)
        result['status'] = STATUS_FAILED
        result['reason'] = str(e)
        result['error_class'] = str(e.__class__.__name__)
        return result

    finally:
        if lock_acquired:
            redis_client.delete(lock_key)
        final_status = result.get('status', STATUS_FAILED)
        set_status(message_id, 'by-msg-id', final_status)
        set_status(data_id, 'by-data-id', final_status)
        set_status(filehash, 'by-hash', final_status)


# @ prov_dm_wrapper
@app.task
def decode_and_ingest(result):
    if result.get('status') != STATUS_SUCCESS:
        LOGGER.info(
            f"Skipping decode for job {result.get('id')} due to previous status: {result.get('status')}")
        return result

    LOGGER.info(f"Starting decode and ingest for {result.get('filepath')}")
    # Add your data decoding and ingestion logic here
    return result
