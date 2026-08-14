#!/bin/sh
set -eu

export SEARXNG_SECRET="${SEARXNG_SECRET:-$(head -c 32 /dev/urandom | base64 | tr -d '\n')}"

# The upstream image declares /etc/searxng as a volume, so install the managed
# config into that runtime volume before handing control back upstream.
cp /opt/lineageweave/settings.yml /etc/searxng/settings.yml

exec /usr/local/searxng/entrypoint.sh "$@"
