from task_manager.tasks import wis2

DATA_ID = "wis2/x/data/obs-1"


def _job(msg_id, rel, pubtime, value):
    return {
        "topic": "cache/a/wis2/x/data/core/obs", "target": "t", "filter": {},
        "_broker": "b", "_received": "r", "_queued": "q",
        "payload": {
            "id": msg_id,
            "properties": {"data_id": DATA_ID, "pubtime": pubtime,
                           "integrity": {"method": "sha512", "value": value}},
            "links": [{"rel": rel, "href": f"http://example.org/{DATA_ID}.bufr"}],
        },
    }


def _mark_original_processed(pubtime):
    wis2.set_status(DATA_ID, "by-data-id", wis2.STATUS_SUCCESS, pubtime=pubtime)


def test_update_newer_than_original_is_downloaded(request_mock):
    _mark_original_processed("2026-09-29T10:00:00Z")

    wis2.download_from_wis2.run(_job("m2", "update", "2026-09-29T10:30:00Z", "hash-2"))

    request_mock.assert_called_once()


def test_update_not_newer_is_skipped(request_mock):
    _mark_original_processed("2026-09-29T10:30:00Z")

    result = wis2.download_from_wis2.run(_job("m3", "update", "2026-09-29T10:00:00Z", "hash-3"))

    assert result["error_class"] == "OutdatedUpdate"
    request_mock.assert_not_called()


def test_canonical_duplicate_still_skipped(request_mock):
    _mark_original_processed("2026-09-29T10:00:00Z")

    result = wis2.download_from_wis2.run(_job("m4", "canonical", "2026-09-29T10:30:00Z", "hash-4"))

    assert result["error_class"] == "PreviouslyProcessed"
    request_mock.assert_not_called()


def test_repeated_update_skipped_by_hash(request_mock):
    _mark_original_processed("2026-09-29T10:00:00Z")
    wis2.set_status("hash-2", "by-hash", wis2.STATUS_SUCCESS)

    result = wis2.download_from_wis2.run(_job("m5", "update", "2026-09-29T10:30:00Z", "hash-2"))

    assert result["error_class"] == "PreviouslyProcessed"
    request_mock.assert_not_called()


def test_success_stores_pubtime(request_mock):
    wis2.set_status(DATA_ID, "by-data-id", wis2.STATUS_SUCCESS, pubtime="2026-09-29T10:00:00Z")

    assert wis2.get_pubtime(DATA_ID) == "2026-09-29T10:00:00Z"


def test_is_newer():
    assert wis2._is_newer("2026-09-29T10:30:00Z", "2026-09-29T10:00:00Z")
    assert not wis2._is_newer("2026-09-29T10:00:00Z", "2026-09-29T10:00:00Z")
    assert wis2._is_newer(None, "2026-09-29T10:00:00Z")
    assert wis2._is_newer("not-a-date", "2026-09-29T10:00:00Z")
    assert not wis2._is_newer("2026-09-29T10:00:00", "2026-09-29T10:00:00Z")
