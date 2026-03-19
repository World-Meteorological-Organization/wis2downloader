#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
    echo ".env already exists — remove it first if you want to regenerate secrets."
    exit 1
fi

cp default.env .env

sed -i "s/FLASK_SECRET_KEY=.*/FLASK_SECRET_KEY=\"$(openssl rand -hex 32)\"/" .env
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=\"$(openssl rand -hex 16)\"/" .env
sed -i "s/GF_SECURITY_ADMIN_PASSWORD=.*/GF_SECURITY_ADMIN_PASSWORD=\"$(openssl rand -hex 32)\"/" .env


echo ".env created with generated secrets."

read -p "Enter download path in host (or press Enter to use default from .env): " HOST_DATA_PATH
if [ ! -z "$HOST_DATA_PATH" ]; then
    if grep -q '^HOST_DATA_PATH=' .env; then
        sed -i "s|^HOST_DATA_PATH=.*$|HOST_DATA_PATH=\"$HOST_DATA_PATH\"|" .env
    else
        echo "HOST_DATA_PATH=\"$HOST_DATA_PATH\"" >> .env
    fi
    echo "HOST_DATA_PATH set to $HOST_DATA_PATH in .env."
else
    echo "Using default HOST_DATA_PATH from .env."
fi

echo "Review .env and adjust any settings before running: docker compose up -d"
