import os

import pytest

from modules.ui.download_files import (
    resolve_download_path,
    search_download_files,
    sort_directory_entries,
    sort_download_files,
)


def test_resolve_download_path_accepts_files_below_root(tmp_path):
    nested_dir = tmp_path / '2026' / '11'
    nested_dir.mkdir(parents=True)
    file_path = nested_dir / 'sample.bufr4'
    file_path.write_bytes(b'data')

    assert resolve_download_path('2026/11/sample.bufr4', tmp_path) == file_path


@pytest.mark.parametrize('relative_path', ('../outside.txt', '/etc/passwd', ''))
def test_resolve_download_path_rejects_invalid_paths(tmp_path, relative_path):
    with pytest.raises(FileNotFoundError):
        resolve_download_path(relative_path, tmp_path)


def test_resolve_download_path_rejects_symlinks_outside_root(tmp_path):
    outside_file = tmp_path.parent / f'{tmp_path.name}-outside.txt'
    outside_file.write_text('not a download')
    (tmp_path / 'outside-link').symlink_to(outside_file)

    with pytest.raises(FileNotFoundError):
        resolve_download_path('outside-link', tmp_path)


def test_search_download_files_is_recursive_and_case_insensitive(tmp_path):
    nested_dir = tmp_path / '2026' / '11'
    nested_dir.mkdir(parents=True)
    matching_file = nested_dir / 'Sample.BUFR4'
    matching_file.write_bytes(b'data')
    (tmp_path / 'other.txt').write_text('not a match')

    assert search_download_files('sample', tmp_path) == [matching_file]


def test_search_download_files_does_not_follow_symlinks(tmp_path):
    outside_dir = tmp_path.parent / f'{tmp_path.name}-outside'
    outside_dir.mkdir()
    (outside_dir / 'sample.bufr4').write_text('outside')
    (tmp_path / 'outside-link').symlink_to(outside_dir, target_is_directory=True)

    assert search_download_files('sample', tmp_path) == []


def test_search_download_files_can_be_sorted_by_modification_time(tmp_path):
    older = tmp_path / 'older.bufr4'
    newer = tmp_path / 'newer.bufr4'
    older.write_bytes(b'old')
    newer.write_bytes(b'new')
    older_time = 1_700_000_000
    newer_time = 1_700_000_100
    os.utime(older, (older_time, older_time))
    os.utime(newer, (newer_time, newer_time))

    files = search_download_files('.bufr4', tmp_path)

    assert sort_download_files(files, True, tmp_path) == [newer, older]
    assert sort_download_files(files, False, tmp_path) == [older, newer]


def test_directory_sort_toggle_sorts_folders_and_keeps_them_before_files(tmp_path):
    older_folder = tmp_path / 'older-folder'
    newer_folder = tmp_path / 'newer-folder'
    older_folder.mkdir()
    newer_folder.mkdir()
    older_file = tmp_path / 'older.bufr4'
    newer_file = tmp_path / 'newer.bufr4'
    older_file.write_text('old')
    newer_file.write_text('new')

    os.utime(older_folder, (1_700_000_000, 1_700_000_000))
    os.utime(newer_folder, (1_700_000_100, 1_700_000_100))
    os.utime(older_file, (1_700_000_000, 1_700_000_000))
    os.utime(newer_file, (1_700_000_100, 1_700_000_100))

    entries = [older_file, older_folder, newer_file, newer_folder]
    assert sort_directory_entries(entries, True) == [
        newer_folder, older_folder, newer_file, older_file
    ]
    assert sort_directory_entries(entries, False) == [
        older_folder, newer_folder, older_file, newer_file
    ]
