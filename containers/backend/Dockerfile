# Single image for the Python back-end services (celery workers/beat, subscriber,
# subscription-manager); each service picks its command in docker-compose.yaml.
# Python comes from Debian (3.13) so apt-get upgrade patches it with the OS.

# Stage 1: build the venv
FROM debian:trixie-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-venv && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY containers/requirements-frozen.txt /tmp/requirements-frozen.txt
RUN pip install -r /tmp/requirements-frozen.txt

COPY modules/shared /src/shared
COPY modules/task_manager /src/task_manager
COPY modules/subscription_manager /src/subscription_manager
COPY modules/subscriber /src/subscriber
RUN pip install --no-deps /src/shared /src/task_manager /src/subscription_manager /src/subscriber && \
    pip uninstall -y pip

# Stage 2: runtime
FROM debian:trixie-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# libmagic1: python-magic; procps: pgrep healthchecks; ca-certificates: broker/download TLS
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends python3 libmagic1 procps ca-certificates && \
    rm -rf /var/lib/apt/lists/*

ARG WIS2DOWNLOADER_GID=988
ARG WIS2DOWNLOADER_UID=10001
RUN groupadd -g ${WIS2DOWNLOADER_GID} wis2 && \
    useradd -u ${WIS2DOWNLOADER_UID} -g wis2 -m -s /usr/sbin/nologin wis2 && \
    chmod 755 /home/wis2

COPY --from=builder /opt/venv /opt/venv

USER wis2
WORKDIR /home/wis2

# Default: subscription-manager API
CMD ["gunicorn", "--config", "python:subscription_manager.gunicorn_conf", "--no-control-socket", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "2", "subscription_manager.app:app"]
