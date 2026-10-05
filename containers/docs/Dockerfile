# Builds the HTML docs; export with: docker build -f containers/docs/Dockerfile --output site .
FROM asciidoctor/docker-asciidoctor:1.103.0 AS build
WORKDIR /repo
COPY docs/ ./docs/
RUN bash docs/build.sh site

# Output stage: only the built site, exported by --output
FROM scratch
COPY --from=build /repo/site /
USER 65534:65534
