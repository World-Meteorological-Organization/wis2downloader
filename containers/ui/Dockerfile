# Stage 1: build docs
FROM asciidoctor/docker-asciidoctor:1.103.0 AS docs-builder
WORKDIR /repo
COPY docs/ ./docs/
RUN chmod +x docs/build.sh && docs/build.sh site

# Stage 2: runtime image
FROM zauberzeug/nicegui:3.8.0

# Set working directory
WORKDIR /app

# Copy the application code to the container
COPY ./modules/ui /app

# Copy local module to the container
COPY ./modules/shared /app/shared

# Bake in the built docs (after COPY ./modules/ui so it is not overwritten)
COPY --from=docs-builder /repo/site /app/site

# Install any additional dependencies if needed
RUN uv pip install /app/shared
RUN uv pip install shapely==2.1.2

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
