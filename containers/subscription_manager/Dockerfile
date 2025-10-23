# Stage 1, building eccodes, eccodes included for future celery use
FROM ubuntu:noble as builder

ENV DEBIAN_FRONTEND="noninteractive" \
    TZ="Etc/UTC" \
    ECCODES_DIR=/opt/eccodes \
    PATH="${PATH}:/opt/eccodes/bin" \
    ECCODES_VER=2.44.0 \
    ECCODES_DEFINITION_PATH=/opt/eccodes/share/eccodes/definitions

SHELL ["/bin/bash", "-c"]

RUN groupadd -g 988 wis2 && \
    useradd -u 10001 -g wis2 -m -s /bin/bash wis2

# install system packages
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends curl build-essential cmake gfortran libffi-dev ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# build and install eccodes
WORKDIR /tmp/eccodes
RUN curl https://confluence.ecmwf.int/download/attachments/45757960/eccodes-${ECCODES_VER}-Source.tar.gz --output eccodes-${ECCODES_VER}-Source.tar.gz && \
    tar xzf eccodes-${ECCODES_VER}-Source.tar.gz && \
    mkdir build && cd build && \
    cmake -DENABLE_AEC=OFF -DCMAKE_INSTALL_PREFIX=${ECCODES_DIR} ../eccodes-${ECCODES_VER}-Source && \
    make && ctest && make install


# stage 2 - setup appliction
FROM ubuntu:noble

ENV DEBIAN_FRONTEND="noninteractive" \
    TZ="Etc/UTC" \
    ECCODES_DIR=/opt/eccodes \
    PATH="${PATH}:/opt/eccodes/bin" \
    ECCODES_DEFINITION_PATH=/opt/eccodes/share/eccodes/definitions \
    PYTHONUNBUFFERED=1 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_metrics


SHELL ["/bin/bash", "-c"]

# Install only runtime dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends python3.12 python3.12-venv python3-pip ca-certificates && \
    rm -rf /var/lib/apt/lists/*


# copy compiled eccodes from build stage
COPY --from=builder /opt/eccodes /opt/eccodes

# Create a non root user
RUN groupadd -g 988 wis2 && \
    useradd -u 10001 -g wis2 -m -s /bin/bash wis2

RUN mkdir -p ${PROMETHEUS_MULTIPROC_DIR} && chown wis2:wis2 ${PROMETHEUS_MULTIPROC_DIR}

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
    pip install -e task_manager && \
    pip install -e subscription_manager

# now the default command
CMD ["/bin/bash", "-c", "source .venv/bin/activate && gunicorn --bind 0.0.0.0:5001 --workers 1 --threads 2 subscription_manager.app:app"]
