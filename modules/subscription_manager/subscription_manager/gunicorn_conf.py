def post_worker_init(worker):
    from subscription_manager.app import start_startup_sync
    start_startup_sync()
