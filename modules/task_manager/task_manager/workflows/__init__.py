from task_manager.tasks.wis2 import download_from_wis2, decode_and_ingest


def wis2_download(args, queue='small_files'):
    workflow = (
        download_from_wis2.s(args).set(queue=queue)
        | decode_and_ingest.s().set(queue=queue)
    )
    return workflow
