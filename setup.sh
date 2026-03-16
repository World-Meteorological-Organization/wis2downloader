#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
    echo ".env already exists — remove it first if you want to regenerate secrets."
    exit 1
fi

cp default.env .env

sed -i "s/FLASK_SECRET_KEY=.*/FLASK_SECRET_KEY=\"$(openssl rand -hex 32)\"/" .env
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=\"$(openssl rand -hex 16)\"/" .env

echo ".env created with generated secrets."

read -p "Enter download path (or press Enter to use default from .env): " DOWNLOAD_PATH
if [ ! -z "$DOWNLOAD_PATH" ]; then
    if grep -q '^DOWNLOAD_PATH=' .env; then
        sed -i "s|^DOWNLOAD_PATH=.*$|DOWNLOAD_PATH=\"$DOWNLOAD_PATH\"|" .env
    else
        echo "DOWNLOAD_PATH=\"$DOWNLOAD_PATH\"" >> .env
    fi
    echo "DOWNLOAD_PATH set to $DOWNLOAD_PATH in .env."
else
    echo "Using default DOWNLOAD_PATH from .env."
fi

echo "Review .env and adjust any settings before running: docker compose up -d"
