"""Save and load subscriptions to a JSON file, with credentials encrypted."""
import datetime as dt
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from shared import setup_logging

LOGGER = setup_logging(__name__)

FILE_VERSION = 1


def _encrypt(sub_data: dict, fernet: Fernet) -> dict:
    out = dict(sub_data)
    creds = out.pop('credentials', None)
    if creds:
        out['credentials_encrypted'] = fernet.encrypt(json.dumps(creds).encode()).decode()
    return out


def _decrypt(sub_id: str, sub_data: dict, fernet: Fernet) -> dict:
    out = dict(sub_data)
    token = out.pop('credentials_encrypted', None)
    out['credentials'] = None
    if token:
        try:
            out['credentials'] = json.loads(fernet.decrypt(token.encode()))
        except InvalidToken:
            LOGGER.error(f"Could not decrypt credentials for subscription {sub_id}, "
                         "restoring without credentials (wrong SUBSCRIPTIONS_ENCRYPTION_KEY?)")
    return out


def write_subscriptions(path: Path, subscriptions: dict, fernet: Fernet) -> None:
    """Write {sub_id: sub_data} to path atomically, readable by owner only."""
    document = {
        'version': FILE_VERSION,
        'saved_at': dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'subscriptions': {k: _encrypt(v, fernet) for k, v in subscriptions.items()},
    }
    tmp_path = path.with_name(f".{path.name}.tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as fh:
        json.dump(document, fh, indent=2)
    os.replace(tmp_path, path)


def read_subscriptions(path: Path, fernet: Fernet) -> dict:
    """Read {sub_id: sub_data} from path, decrypting credentials."""
    document = json.loads(path.read_text())
    if document.get('version') != FILE_VERSION:
        raise ValueError(f"Unsupported subscriptions file version: {document.get('version')}")
    return {k: _decrypt(k, v, fernet) for k, v in document.get('subscriptions', {}).items()}
