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
echo "Review .env and adjust any settings before running: docker compose up -d"
