from task_manager.tasks.wis2 import *

def wis2_download(args):
    workflow = download_from_wis2.s(args) | decode_and_ingest.s()
    return workflow