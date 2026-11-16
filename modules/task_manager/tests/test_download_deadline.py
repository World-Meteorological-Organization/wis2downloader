import time
from unittest.mock import create_autospec

import pytest
import urllib3

from task_manager.tasks import wis2


def _response(chunks):
    response = create_autospec(urllib3.HTTPResponse, instance=True)
    response.stream.return_value = iter(chunks)
    return response


def test_download_within_deadline(tmp_path):
    dest = tmp_path / "file.bin"

    size, _ = wis2._stream_response_to_file(
        _response([b"a" * 10, b"b" * 10]), str(dest), None, "http://x", time.monotonic() + 60)

    assert size == 20
    assert dest.read_bytes() == b"a" * 10 + b"b" * 10


def test_download_past_deadline_raises(tmp_path):
    with pytest.raises(wis2.DownloadTimeoutError):
        wis2._stream_response_to_file(
            _response([b"a" * 10]), str(tmp_path / "file.bin"), None, "http://x", time.monotonic() - 1)


def test_no_deadline(tmp_path):
    size, _ = wis2._stream_response_to_file(
        _response([b"a" * 10]), str(tmp_path / "file.bin"), None, "http://x")

    assert size == 10
