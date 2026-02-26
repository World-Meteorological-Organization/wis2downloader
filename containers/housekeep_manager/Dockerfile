FROM ubuntu:noble

ENV DEBIAN_FRONTEND="noninteractive" \
    TZ="Etc/UTC" \
    PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-c"]

# Install only runtime dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends libmagic1 python3.12 python3.12-venv python3-pip ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create a non root user
RUN groupadd -g 988 wis2 && \
    useradd -u 10001 -g wis2 -m -s /bin/bash wis2

USER wis2
WORKDIR /home/wis2

# add python venv
RUN python3.12 -m venv /home/wis2/.venv && \
    echo "source /home/wis2/.venv/bin/activate" >> .bashrc && \
    echo "" >> .bashrc

COPY --chown=wis2:wis2 ./modules/ ./app

RUN cd ./app && \
    source /home/wis2/.venv/bin/activate && \
    pip install gunicorn gevent && \
    pip install -e shared && \
    pip install -e housekeep_manager && \
    pip install -e subscription_manager

# now the default command
CMD ["/bin/bash", "-c", "source .venv/bin/activate && housekeep_manager_start worker"]
