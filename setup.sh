#!/usr/bin/env bash
set -euo pipefail

ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
if docker plugin ls | grep -q 'loki'; then
    echo "Loki Docker plugin already installed."
else
    docker plugin install grafana/loki-docker-driver:3.6.7-${ARCH} --alias loki --grant-all-permissions
    echo "Loki Docker plugin installed."
fi

# 32 random bytes, url-safe base64 (Fernet key format)
generate_encryption_key() {
    openssl rand -base64 32 | tr '+/' '-_'
}

ADDED=()  # settings added to .env by this run

# Set NAME to VALUE in .env if NAME is missing or empty; existing values are kept
fill_secret() {
    local name="$1" value="$2"
    if ! grep -q "^${name}=.." .env; then
        sed -i "/^${name}=/d" .env
        echo "${name}=\"${value}\"" >> .env
        ADDED+=("$name")
    fi
}

fill_secrets() {
    fill_secret FLASK_SECRET_KEY "$(openssl rand -hex 32)"
    fill_secret VALKEY_PASSWORD "$(openssl rand -hex 16)"
    fill_secret SUBSCRIPTIONS_ENCRYPTION_KEY "$(generate_encryption_key)"
}

# Release bundles run the published images (docker-compose.images.yml) instead of building
use_release_images() {
    if [ -f docker-compose.images.yml ] && ! grep -q "^COMPOSE_FILE=" .env; then
        echo "COMPOSE_FILE=docker-compose.yaml:docker-compose.images.yml" >> .env
        ADDED+=(COMPOSE_FILE)
    fi
}

if [ -f .env ]; then
    fill_secrets
    use_release_images
    if [ ${#ADDED[@]} -eq 0 ]; then
        echo ".env exists and is complete; nothing changed."
    else
        echo ".env exists; added: ${ADDED[*]}. Existing values kept."
    fi
    exit 0
fi

cp default.env .env
fill_secrets
use_release_images

echo ".env created with generated secrets."
echo "Back up SUBSCRIPTIONS_ENCRYPTION_KEY: without it saved credentials cannot be restored."

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

read -p "Enter Grafana admin username (or press Enter to use default 'admin'): " GRAFANA_ADMIN_USER
GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
sed -i "s|^GRAFANA_ADMIN_USER=.*$|GRAFANA_ADMIN_USER=\"$GRAFANA_ADMIN_USER\"|" .env
echo "GRAFANA_ADMIN_USER set to '$GRAFANA_ADMIN_USER' in .env."

read -p "Enter Grafana admin password (or press Enter to auto-generate): " GRAFANA_ADMIN_PASSWORD
if [ -z "$GRAFANA_ADMIN_PASSWORD" ]; then
    GRAFANA_ADMIN_PASSWORD="$(openssl rand -hex 16)"
    echo "Auto-generated Grafana password: $GRAFANA_ADMIN_PASSWORD"
fi
sed -i "s|^GRAFANA_ADMIN_PASSWORD=.*$|GRAFANA_ADMIN_PASSWORD=\"$GRAFANA_ADMIN_PASSWORD\"|" .env
echo "GRAFANA_ADMIN_PASSWORD set in .env."

read -p "Enter UID for file ownership (or press Enter to use current user's UID: $(id -u)): " INPUT_UID
INPUT_UID="${INPUT_UID:-$(id -u)}"
if grep -q '^WIS2DOWNLOADER_UID=' .env; then
    sed -i "s|^WIS2DOWNLOADER_UID=.*$|WIS2DOWNLOADER_UID=\"$INPUT_UID\"|" .env
else
    echo "WIS2DOWNLOADER_UID=\"$INPUT_UID\"" >> .env
fi
echo "WIS2DOWNLOADER_UID set to $INPUT_UID in .env."

read -p "Enter GID for file ownership (or press Enter to use current user's GID: $(id -g)): " INPUT_GID
INPUT_GID="${INPUT_GID:-$(id -g)}"
if grep -q '^WIS2DOWNLOADER_GID=' .env; then
    sed -i "s|^WIS2DOWNLOADER_GID=.*$|WIS2DOWNLOADER_GID=\"$INPUT_GID\"|" .env
else
    echo "WIS2DOWNLOADER_GID=\"$INPUT_GID\"" >> .env
fi
echo "WIS2DOWNLOADER_GID set to $INPUT_GID in .env."

EFFECTIVE_DATA_PATH="${HOST_DATA_PATH:-$(grep '^HOST_DATA_PATH=' .env | cut -d= -f2- | tr -d '"')}"
if [ -n "$EFFECTIVE_DATA_PATH" ]; then
    mkdir -p "$EFFECTIVE_DATA_PATH"
    echo "Download path '$EFFECTIVE_DATA_PATH' created."
fi

SUBSCRIPTIONS_PATH="$(grep '^HOST_SUBSCRIPTIONS_PATH=' .env | cut -d= -f2- | tr -d '"')"
SUBSCRIPTIONS_PATH="${SUBSCRIPTIONS_PATH:-./subscriptions}"
mkdir -p "$SUBSCRIPTIONS_PATH"
chmod 700 "$SUBSCRIPTIONS_PATH"
echo "Subscriptions path '$SUBSCRIPTIONS_PATH' created."

echo "Review .env and adjust any settings before running: docker compose up -d"
