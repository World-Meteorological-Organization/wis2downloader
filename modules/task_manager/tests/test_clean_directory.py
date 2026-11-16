import datetime as dt

import pytest

from task_manager.tasks import scheduled_tasks

RETENTION_HOURS = 48


@pytest.fixture
def gauge(monkeypatch):
    """Capture disk_downloads_bytes adjustments instead of writing to Valkey."""
    calls = []
    monkeypatch.setattr(scheduled_tasks, 'incr_counter',
                        lambda name, labels, value=1: calls.append((name, value)))
    monkeypatch.setattr(scheduled_tasks, 'RETENTION_PERIOD_HOURS', RETENTION_HOURS)
    return calls


def _cutoff() -> dt.date:
    now = dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(hours=RETENTION_HOURS)).date()


def _day_dir(root, target: str, day: dt.date):
    path = root / target / f"{day:%Y/%m/%d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path, size: int):
    path.write_bytes(b"x" * size)
    return path


def test_deletes_days_before_cutoff_and_keeps_cutoff_day(tmp_path, gauge):
    cutoff = _cutoff()
    expired = _day_dir(tmp_path, "bufr", cutoff - dt.timedelta(days=1))
    kept = _day_dir(tmp_path, "bufr", cutoff)
    _write(expired / "old.bufr", 100)
    _write(kept / "new.bufr", 10)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert not expired.exists()
    assert (kept / "new.bufr").exists()


def test_gauge_decremented_by_bytes_freed(tmp_path, gauge):
    expired = _day_dir(tmp_path, "bufr", _cutoff() - dt.timedelta(days=3))
    _write(expired / "a.bufr", 100)
    _write(expired / "b.bufr", 50)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert gauge == [('disk_downloads_bytes', -150)]


def test_no_gauge_update_when_nothing_expired(tmp_path, gauge):
    _write(_day_dir(tmp_path, "bufr", _cutoff()) / "new.bufr", 10)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert gauge == []


def test_empty_month_and_year_removed_but_target_kept(tmp_path, gauge):
    old = dt.date(2020, 1, 15)
    _write(_day_dir(tmp_path, "grib", old) / "old.grib", 10)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert not (tmp_path / "grib" / "2020").exists()
    assert (tmp_path / "grib").is_dir()


def test_month_kept_while_it_has_other_days(tmp_path, gauge):
    cutoff = _cutoff()
    _write(_day_dir(tmp_path, "bufr", cutoff - dt.timedelta(days=1)) / "old.bufr", 10)
    kept = _day_dir(tmp_path, "bufr", cutoff)
    _write(kept / "new.bufr", 10)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert kept.is_dir()


def test_nested_target(tmp_path, gauge):
    expired = _day_dir(tmp_path, "centre/a/bufr", dt.date(2020, 1, 15))
    _write(expired / "old.bufr", 10)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert not expired.exists()
    assert (tmp_path / "centre" / "a" / "bufr").is_dir()


def test_leftover_temp_files_and_subdirectories_removed(tmp_path, gauge):
    expired = _day_dir(tmp_path, "bufr", dt.date(2020, 1, 15))
    _write(expired / ".tmp_abc123", 5)
    (expired / "sub").mkdir()
    _write(expired / "sub" / "x.bin", 5)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert not expired.exists()
    assert gauge == [('disk_downloads_bytes', -10)]


def test_files_outside_date_layout_untouched(tmp_path, gauge):
    (tmp_path / "bufr").mkdir()
    loose = _write(tmp_path / "bufr" / "loose.bufr", 10)
    not_a_date = tmp_path / "bufr" / "2020" / "13" / "40"
    not_a_date.mkdir(parents=True)
    odd = _write(not_a_date / "odd.bufr", 10)

    scheduled_tasks.clean_directory(str(tmp_path))

    assert loose.exists()
    assert odd.exists()
    assert gauge == []


def test_as_date():
    assert scheduled_tasks._as_date("2026", "09", "29") == dt.date(2026, 9, 29)
    assert scheduled_tasks._as_date("2026", "02", "30") is None
    assert scheduled_tasks._as_date("2026", "9", "29") is None
    assert scheduled_tasks._as_date("bufr", "09", "29") is None
