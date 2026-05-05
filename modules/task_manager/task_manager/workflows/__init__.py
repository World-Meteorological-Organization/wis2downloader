from task_manager.tasks.wis2 import download_from_wis2, decode_and_ingest


def wis2_download(args):
    workflow = download_from_wis2.s(args) | decode_and_ingest.s()
    return workflow
