#!/bin/sh
# Check that the durable worker heartbeat advanced without importing Python.
#
# The worker writes a trusted monotonic integer. This probe keeps the same
# progress contract as backend.app.worker_health while avoiding a Python
# interpreter and package import for every container health check.

set -eu

heartbeat_path=${1:-/tmp/lineageweave-worker-heartbeat}
state_path=${2:-/tmp/lineageweave-worker-healthcheck-state}

current_sample=$(cat "$heartbeat_path" 2>/dev/null) || exit 1
set -- $current_sample
[ "$#" -eq 3 ] || exit 1
current_version=$1
current_epoch=$2
current_heartbeat=$3
[ "$current_version" = v1 ] || exit 1
[ "${#current_epoch}" -eq 32 ] || exit 1
case "$current_epoch" in ''|*[!0-9a-f]*) exit 1 ;; esac
case "$current_heartbeat" in ''|*[!0-9]*) exit 1 ;; esac

if previous_sample=$(cat "$state_path" 2>/dev/null); then
    set -- $previous_sample
    if [ "$#" -eq 3 ]; then
        previous_version=$1
        previous_epoch=$2
        previous_heartbeat=$3
        case "$previous_heartbeat" in ''|*[!0-9]*) previous_heartbeat= ;; esac
        if [ "$previous_version" = v1 ] \
            && [ "$previous_epoch" = "$current_epoch" ] \
            && [ -n "$previous_heartbeat" ] \
            && [ "$current_heartbeat" -le "$previous_heartbeat" ]; then
            exit 1
        fi
    fi
fi

temporary_state="${state_path}.$$"
trap 'rm -f "$temporary_state"' EXIT HUP INT TERM
printf '%s\n' "$current_sample" > "$temporary_state"
mv "$temporary_state" "$state_path"
trap - EXIT HUP INT TERM
