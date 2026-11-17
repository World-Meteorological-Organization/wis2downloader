from task_manager.tasks.wis2 import download_from_wis2
from shared.queues import DEFAULT_QUEUE


def wis2_download(args, queue=DEFAULT_QUEUE):
    return download_from_wis2.s(args).set(queue=queue)
