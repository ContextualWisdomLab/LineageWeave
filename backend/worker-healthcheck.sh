#!/bin/sh
# Check that the durable worker heartbeat advanced without importing Python.
#
# The worker writes a trusted monotonic integer. This probe keeps the same
# progress contract as backend.app.worker_health while avoiding a Python
# interpreter and package import for every container health check.

set -eu

heartbeat_path=${1:-/tmp/lineageweave-worker-heartbeat}
state_path=${2:-/tmp/lineageweave-worker-healthcheck-state}

decimal_le_same_width() {
    left=$1
    right=$2
    while [ -n "$left" ]; do
        left_digit=${left%"${left#?}"}
        right_digit=${right%"${right#?}"}
        if [ "$left_digit" -lt "$right_digit" ]; then
            return 0
        fi
        if [ "$left_digit" -gt "$right_digit" ]; then
            return 1
        fi
        left=${left#?}
        right=${right#?}
    done
    return 0
}

valid_counter() {
    value=$1
    case "$value" in ''|*[!0-9]*) return 1 ;; esac
    [ "${#value}" -le 19 ] || return 1
    if [ "${#value}" -eq 19 ]; then
        decimal_le_same_width "$value" 9223372036854775807 || return 1
    fi
}

current_sample=$(cat "$heartbeat_path" 2>/dev/null) || exit 1
set -- $current_sample
[ "$#" -eq 3 ] || exit 1
current_version=$1
current_epoch=$2
current_heartbeat=$3
[ "$current_version" = v1 ] || exit 1
[ "${#current_epoch}" -eq 32 ] || exit 1
case "$current_epoch" in ''|*[!0-9a-f]*) exit 1 ;; esac
valid_counter "$current_heartbeat" || exit 1

if previous_sample=$(cat "$state_path" 2>/dev/null); then
    set -- $previous_sample
    if [ "$#" -eq 3 ]; then
        previous_version=$1
        previous_epoch=$2
        previous_heartbeat=$3
        [ "$previous_version" = v1 ] || exit 1
        [ "${#previous_epoch}" -eq 32 ] || exit 1
        case "$previous_epoch" in ''|*[!0-9a-f]*) exit 1 ;; esac
        valid_counter "$previous_heartbeat" || exit 1
        if [ "$previous_epoch" = "$current_epoch" ] \
            && [ "$current_heartbeat" -le "$previous_heartbeat" ]; then
            exit 1
        fi
    else
        exit 1
    fi
fi

temporary_state="${state_path}.$$"
trap 'rm -f "$temporary_state"' EXIT HUP INT TERM
printf '%s\n' "$current_sample" > "$temporary_state"
mv "$temporary_state" "$state_path"
trap - EXIT HUP INT TERM
