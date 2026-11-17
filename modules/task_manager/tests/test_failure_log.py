import logging

from task_manager.tasks import wis2


def _wrapped(result, monkeypatch):
    monkeypatch.setattr(wis2, "incr_counter", lambda *a, **k: None)
    return wis2.metrics_collector(lambda: result)


def test_failed_result_logged(monkeypatch, caplog):
    result = {'status': wis2.STATUS_FAILED, 'error_class': 'HTTPError', 'reason': 'HTTP 404',
              'id': 'msg-1', 'data_id': 'd-1', 'global_cache': 'cache.example',
              'download_url': 'https://cache.example/f.bufr'}

    with caplog.at_level(logging.WARNING):
        _wrapped(result, monkeypatch)()

    assert any(r.getMessage() == "Download failed: HTTPError: HTTP 404 (id=msg-1, data_id=d-1, "
               "cache=cache.example, url=https://cache.example/f.bufr)" for r in caplog.records)


def test_success_and_skip_not_logged(monkeypatch, caplog):
    with caplog.at_level(logging.WARNING):
        _wrapped({'status': wis2.STATUS_SUCCESS}, monkeypatch)()
        _wrapped({'status': wis2.STATUS_SKIPPED}, monkeypatch)()

    assert not [r for r in caplog.records if r.getMessage().startswith("Download failed")]
