# Stage 1: build docs
FROM --platform=$BUILDPLATFORM asciidoctor/docker-asciidoctor:1.103.0 AS docs-builder
WORKDIR /repo
COPY docs/ ./docs/
RUN chmod +x docs/build.sh && docs/build.sh site

# Stage 2: runtime image
FROM zauberzeug/nicegui:3.17.1

# Pick up Debian security fixes not yet in the base image
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the application code to the container
COPY ./modules/ui /app

# Copy local module to the container
COPY ./modules/shared /app/shared

# Bake in the built docs (after COPY ./modules/ui so it is not overwritten)
COPY --from=docs-builder /repo/site /app/site

# Install extra dependencies; anyio/lxml_html_clean pinned above NiceGUI's minimums for CVE fixes.
# System pip (vendors old urllib3/msgpack/setuptools) is unused at runtime, so remove it.
RUN uv pip install --no-cache /app/shared shapely==2.1.2 anyio==4.14.2 lxml_html_clean==0.4.5 && \
    /usr/local/bin/python3 -m pip uninstall -y pip

# Create a non root user; it owns /app as NiceGUI writes .nicegui/ storage there
ARG WIS2DOWNLOADER_GID=988
ARG WIS2DOWNLOADER_UID=10001
RUN groupadd -g ${WIS2DOWNLOADER_GID} wis2 && \
    useradd -u ${WIS2DOWNLOADER_UID} -g wis2 -m -s /bin/bash wis2 && \
    chown -R wis2:wis2 /app

USER wis2

# Expose the port your NiceGUI app runs on (default is 8080)
EXPOSE 8080

# Set the default command to run the NiceGUI app
# The base entrypoint needs root to drop privileges; not needed with USER set
ENTRYPOINT []
CMD ["/opt/venv/bin/python", "main.py"]
