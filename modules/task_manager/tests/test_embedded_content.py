import base64
import datetime as dt
import gzip
import hashlib

from task_manager.tasks import wis2

DATA = b"hello wis2\n"


def _content(encoding, value, size=len(DATA)):
    return {"encoding": encoding, "value": value, "size": size}


def _gzip_b64(data):
    return base64.b64encode(gzip.compress(data)).decode()


def test_decode_utf8():
    assert wis2._decode_content(_content("utf-8", DATA.decode())) == DATA


def test_decode_base64():
    assert wis2._decode_content(_content("base64", base64.b64encode(DATA).decode())) == DATA


def test_decode_gzip():
    assert wis2._decode_content(_content("gzip", _gzip_b64(DATA))) == DATA


def test_absent_content():
    assert wis2._decode_content(None) is None


def test_size_mismatch_rejected():
    assert wis2._decode_content(_content("base64", base64.b64encode(DATA).decode(), size=3)) is None


def test_gzip_larger_than_declared_rejected():
    bomb = _gzip_b64(b"\0" * 10_000_000)

    assert wis2._decode_content(_content("gzip", bomb, size=100)) is None


def test_invalid_encoding_rejected():
    assert wis2._decode_content(_content("rot13", "uryyb")) is None
    assert wis2._decode_content(_content("base64", "not base64!")) is None


def _job(content):
    return {
        "topic": "cache/a/wis2/x/data/core/obs", "target": "t", "filter": {},
        "_broker": "b", "_received": "r", "_queued": "q",
        "payload": {
            "id": "m1",
            "properties": {
                "data_id": "wis2/x/data/obs-2", "pubtime": "2026-09-29T10:00:00Z",
                "integrity": {"method": "sha512", "value": base64.b64encode(hashlib.sha512(DATA).digest()).decode()},
                "content": content,
            },
            "links": [{"rel": "canonical", "href": "http://example.org/obs-2.txt"}],
        },
    }


def test_task_uses_embedded_content(request_mock, tmp_path):
    result = wis2.download_from_wis2.run(_job(_content("gzip", _gzip_b64(DATA))))

    assert result["status"] == wis2.STATUS_SUCCESS
    assert result["valid_hash"]
    request_mock.assert_not_called()
    assert (tmp_path / "t" / f"{dt.date.today():%Y/%m/%d}" / "obs-2.txt").read_bytes() == DATA


def test_task_falls_back_to_link_when_content_invalid(request_mock):
    wis2.download_from_wis2.run(_job(_content("base64", "not base64!")))

    request_mock.assert_called_once()
