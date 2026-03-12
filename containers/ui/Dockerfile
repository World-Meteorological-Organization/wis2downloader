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

# Expose the port your NiceGUI app runs on (default is 8080)
EXPOSE 8080

# Set the default command to run the NiceGUI app
CMD ["/opt/venv/bin/python", "main.py"]
