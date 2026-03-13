#!/usr/bin/env bash
set -euo pipefail
OUTPUT="${1:-site}"
BASE_OPTS="-a toclevels=3 -a icons=font -a stylesheet=../assets/wmo-asciidoc.css"

for lang in en fr es ar zh ru; do
    src="docs/$lang"
    [ -d "$src" ] || continue
    mkdir -p "$OUTPUT/$lang"
    asciidoctor $BASE_OPTS -D "$OUTPUT/$lang" "$src"/*.adoc
done

# Post-process Arabic HTML files to fix lang and add dir="rtl"
for f in "$OUTPUT/ar"/*.html; do
    [ -f "$f" ] || continue
    sed -i 's/<html lang="en">/<html lang="ar" dir="rtl">/' "$f"
done

# Post-process other languages to set correct lang attribute
for lang in fr es zh ru; do
    for f in "$OUTPUT/$lang"/*.html; do
        [ -f "$f" ] || continue
        sed -i "s/<html lang=\"en\">/<html lang=\"$lang\">/" "$f"
    done
done

asciidoctor $BASE_OPTS -D "$OUTPUT" docs/index.adoc
echo "Docs built → $OUTPUT/"

