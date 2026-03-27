import os

SUBSCRIPTION_MANAGER = str(
    os.getenv("WIS2DOWNLOADER_SUBSCRIPTION_MANAGER_URL", "http://traefik/api")
)
