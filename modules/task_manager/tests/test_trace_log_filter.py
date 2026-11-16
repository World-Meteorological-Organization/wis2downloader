import logging

from task_manager.worker import OmitReturnValue

LOG_SUCCESS = "Task %(name)s[%(id)s] succeeded in %(runtime)ss: %(return_value)s"


def _record(name):
    args = {'id': 'abc', 'name': name, 'return_value': "{'id': 'x'}", 'runtime': 0.1}
    return logging.LogRecord('celery.app.trace', logging.INFO, __file__, 1, LOG_SUCCESS, (args,), None)


def test_download_task_return_value_omitted():
    record = _record('task_manager.tasks.wis2.download_from_wis2')

    assert OmitReturnValue().filter(record)
    assert record.getMessage() == (
        "Task task_manager.tasks.wis2.download_from_wis2[abc] succeeded in 0.1s: <omitted>")


def test_other_task_unchanged():
    record = _record('task_manager.tasks.scheduled_tasks.clean_directory')

    assert OmitReturnValue().filter(record)
    assert record.getMessage().endswith(": {'id': 'x'}")


def test_non_mapping_args_unchanged():
    record = logging.LogRecord('celery.app.trace', logging.INFO, __file__, 1, "x %s", ('y',), None)

    assert OmitReturnValue().filter(record)
    assert record.getMessage() == "x y"
