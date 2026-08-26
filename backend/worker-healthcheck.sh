#!/bin/sh
# Check that the durable worker heartbeat advanced without importing Python.
#
# The worker writes a trusted monotonic integer. This probe keeps the same
# progress contract as backend.app.worker_health while avoiding a Python
# interpreter and package import for every container health check.

set -eu

heartbeat_path=${1:-/tmp/lineageweave-worker-heartbeat}
state_path=${2:-/tmp/lineageweave-worker-healthcheck-state}

current_heartbeat=$(cat "$heartbeat_path" 2>/dev/null) || exit 1
case "$current_heartbeat" in
    ''|*[!0-9]*) exit 1 ;;
esac

if IFS= read -r previous_heartbeat 2>/dev/null < "$state_path"; then
    case "$previous_heartbeat" in
        ''|*[!0-9]*) previous_heartbeat= ;;
    esac
    if [ -n "$previous_heartbeat" ] && [ "$current_heartbeat" -le "$previous_heartbeat" ]; then
        exit 1
    fi
fi

temporary_state="${state_path}.$$"
printf '%s\n' "$current_heartbeat" > "$temporary_state"
mv "$temporary_state" "$state_path"
