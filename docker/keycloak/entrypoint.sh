#!/bin/sh
set -eu

realm_file=/opt/keycloak/data/import/realm-export.json
audience=${MCP_RESOURCE_URL:-http://localhost:18001/mcp}

case "$audience" in
  *\"*|*\\*|*' '*|*'	'*)
    echo "MCP_RESOURCE_URL contains characters unsafe for the realm JSON" >&2
    exit 1
    ;;
esac

escaped_audience=$(printf '%s' "$audience" | sed 's/[\\&|]/\\&/g')
sed -i "s|__MCP_RESOURCE_URL__|$escaped_audience|g" "$realm_file"
exec /opt/keycloak/bin/kc.sh "$@"
