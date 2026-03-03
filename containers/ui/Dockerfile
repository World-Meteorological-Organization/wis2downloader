# Stage 1: build docs
FROM ruby:3.3-alpine AS docs-builder
RUN gem install asciidoctor
WORKDIR /repo
COPY docs/ ./docs/
RUN set -e; for lang in en fr es ar zh ru; do \
      [ -d docs/$lang ] || continue; \
      mkdir -p site/$lang; \
      asciidoctor -a toc=left -a toclevels=3 -a icons=font \
                  -D site/$lang docs/$lang/*.adoc; \
    done; \
    asciidoctor -a toc=left -D site docs/index.adoc

# Stage 2: runtime image
FROM zauberzeug/nicegui:latest

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
RUN uv pip install shapely

# Expose the port your NiceGUI app runs on (default is 8080)
EXPOSE 8080

# Set the default command to run the NiceGUI app
CMD ["/opt/venv/bin/python", "main.py"]
