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

# Install extra dependencies; anyio/lxml_html_clean pinned above NiceGUI's minimums for CVE fixes.
# System pip (vendors old urllib3/msgpack/setuptools) is unused at runtime, so remove it.
RUN uv pip install --no-cache /app/shared shapely==2.1.2 anyio==4.14.2 lxml_html_clean==0.4.5 && \
    /usr/local/bin/python3 -m pip uninstall -y pip

# Non-root user; /app stays root-owned and read-only (the UI writes nothing)
ARG WIS2DOWNLOADER_GID=988
ARG WIS2DOWNLOADER_UID=10001
RUN groupadd -g ${WIS2DOWNLOADER_GID} wis2 && \
    useradd -u ${WIS2DOWNLOADER_UID} -g wis2 -m -s /usr/sbin/nologin wis2

USER wis2

# Docs version the Help link opens; release builds pass their version
ARG DOCS_VERSION=latest
ENV WIS2DOWNLOADER_DOCS_VERSION=${DOCS_VERSION}

# Expose the port your NiceGUI app runs on (default is 8080)
EXPOSE 8080

# Static asset, not '/': each page request builds a NiceGUI client
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["/opt/venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/assets/base.css', timeout=4)"]

# Set the default command to run the NiceGUI app
# The base entrypoint needs root to drop privileges; not needed with USER set
ENTRYPOINT []
CMD ["/opt/venv/bin/python", "main.py"]
