#!/usr/bin/env bash
# Update a release install to the newest patch release of its version line (e.g. 1.0.x).
# Patch releases change images only; a new minor/major release needs a new release bundle.
set -euo pipefail

REPO="World-Meteorological-Organization/wis2downloader"
IMAGES_FILE="docker-compose.images.yml"

if [ ! -f VERSION ]; then
    echo "No VERSION file: this is a source checkout. Update with git and run: docker compose build"
    exit 1
fi

if ! grep -q "^COMPOSE_FILE=.*${IMAGES_FILE}" .env 2>/dev/null; then
    echo ".env does not use ${IMAGES_FILE}: run setup.sh first."
    exit 1
fi

current="$(tr -d '[:space:]' < VERSION)"
if [[ ! "$current" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Version ${current} is a pre-release: download the new release bundle to update."
    exit 1
fi
line="${current%.*}"

# Newest final release on this line; pre-releases never match the pattern
latest="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases?per_page=100" \
    | grep -oE "\"tag_name\": *\"v${line//./\\.}\.[0-9]+\"" \
    | grep -oE "[0-9]+\.[0-9]+\.[0-9]+" \
    | sort -V | tail -n 1 || true)"

if [ -z "$latest" ] || [ "$(printf '%s\n%s\n' "$current" "$latest" | sort -V | tail -n 1)" = "$current" ]; then
    echo "Already on the newest ${line}.x release (${current})."
    exit 0
fi

echo "Updating ${current} -> ${latest}"
trap 'rm -f "${IMAGES_FILE}.new"' EXIT
curl -fsSL -o "${IMAGES_FILE}.new" \
    "https://github.com/${REPO}/releases/download/v${latest}/${IMAGES_FILE}"

# Pull with the new file first; the install is only switched once all images are present
docker compose -f docker-compose.yaml -f "${IMAGES_FILE}.new" pull
cp "$IMAGES_FILE" "${IMAGES_FILE}.${current}.bak"
mv "${IMAGES_FILE}.new" "$IMAGES_FILE"
echo "$latest" > VERSION
echo "Images for ${latest} pulled; previous images file kept as ${IMAGES_FILE}.${current}.bak"
read -r -p "Restart services now? [y/N] " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    docker compose up -d
else
    echo "Run 'docker compose up -d' to switch to ${latest}."
fi
