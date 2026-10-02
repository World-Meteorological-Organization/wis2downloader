import logging

import pytest

from shared.logging import setup_logging


@pytest.fixture(autouse=True)
def restore_root():
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def _clear_root():
    # pytest adds its own capture handler to root while a test runs
    logging.getLogger().handlers.clear()


def test_root_and_named_logger_print_once(capsys):
    _clear_root()
    setup_logging()
    logger = setup_logging("test.once")

    logger.info("hello")

    assert capsys.readouterr().out.count("hello") == 1


def test_named_logger_without_root_setup_prints_once(capsys):
    _clear_root()
    logger = setup_logging("test.named_only")
    setup_logging("test.named_only.other")

    logger.info("hello")

    assert capsys.readouterr().out.count("hello") == 1


def test_repeated_root_setup_does_not_add_handlers():
    _clear_root()
    setup_logging()
    setup_logging()

    assert len(logging.getLogger().handlers) == 1
