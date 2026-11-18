import logging
import os
from pathlib import Path, PurePosixPath


DOWNLOADS_ROOT = Path(os.getenv('CONTAINER_DATA_PATH', '/data'))
LOGGER = logging.getLogger(__name__)


def resolve_download_path(relative_path: str, root: Path = DOWNLOADS_ROOT) -> Path:
    """Resolve a file below the downloads root without following paths outside it."""
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise FileNotFoundError(relative_path)

    try:
        resolved_root = root.resolve(strict=True)
        resolved_path = (resolved_root / Path(*relative.parts)).resolve(strict=True)
    except RuntimeError as exc:
        raise FileNotFoundError(relative_path) from exc
    if not resolved_path.is_relative_to(resolved_root):
        raise FileNotFoundError(relative_path)
    return resolved_path


def search_download_files(query: str, root: Path = DOWNLOADS_ROOT) -> list[Path]:
    """Find regular files whose names contain query, without following symlinks."""
    search_term = query.casefold()
    resolved_root = root.resolve(strict=True)
    matches = []

    def log_walk_error(error: OSError):
        LOGGER.warning('Unable to search downloads directory %s: %s', error.filename, error)

    for current_dir, directories, filenames in os.walk(
        resolved_root, followlinks=False, onerror=log_walk_error
    ):
        directories[:] = [
            name for name in directories
            if not (Path(current_dir) / name).is_symlink()
        ]
        for filename in filenames:
            path = Path(current_dir) / filename
            if search_term in filename.casefold() and not path.is_symlink() and path.is_file():
                matches.append(path)
    return matches


def sort_download_files(
    files: list[Path], newest_first: bool = True, root: Path = DOWNLOADS_ROOT
) -> list[Path]:
    """Sort files by modification time with a stable relative-path tie-breaker."""
    resolved_root = root.resolve(strict=True)
    return sorted(
        files,
        key=lambda path: (
            -path.stat().st_mtime if newest_first else path.stat().st_mtime,
            path.relative_to(resolved_root).as_posix().casefold(),
        ),
    )


def sort_directory_entries(
    entries: list[Path], newest_first: bool = True
) -> list[Path]:
    """Keep folders first, sorting both folders and files by modification time."""
    return sorted(
        entries,
        key=lambda path: (
            not path.is_dir(),
            -path.stat().st_mtime if newest_first else path.stat().st_mtime,
            path.name.casefold(),
        ),
    )
