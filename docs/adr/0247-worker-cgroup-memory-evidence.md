# ADR 0247: Worker cgroup memory evidence before capacity limits

- Status: Accepted
- Date: 2026-08-27

## Context

The canonical worker was once observed with exit code 137 and was later
recreated healthy. Exit 137 establishes a `SIGKILL`, not its cause. Recreation
also discards the prior container's Docker state and cgroup counters, so the
new container's `OOMKilled=false` cannot disprove a historical OOM.

The base Compose service has no worker-specific memory limit or reservation.
Docker therefore exposes the Docker Desktop VM capacity, not an accepted
worker capacity envelope. Setting `mem_limit` from the current idle footprint,
an arbitrary percentage, or an undocumented headroom multiplier would turn an
unrepresentative observation into a production failure boundary.

## Decision

`scripts/capture_worker_memory_evidence.py` is the canonical worker-memory
measurement procedure. It captures two snapshots around an explicitly chosen
representative workload window from the unchanged `lineageweave` worker:

- Docker status, exit code, `OOMKilled`, restart count, and configured memory
  limit/reservation;
- cgroup v2 `memory.current`, `memory.peak`, `memory.max`, and the keyed local
  event counters in `memory.events.local`.

The procedure rejects a container replacement, unavailable cgroup v2
evidence, decreasing counters, and non-positive windows. It classifies OOM as
confirmed only when Docker records `OOMKilled` or the kernel's local
`oom_kill` counter increases. Exit 137 without either signal remains
`sigkill_unattributed`. `high`, `max`, or `oom` deltas establish memory
pressure without inventing an OOM kill.

If the unchanged worker exits during the window, Compose discovery includes
stopped containers and Docker inspection preserves its terminal state. The
terminated cgroup is no longer readable, so ending current usage and event
deltas remain `null`; the output retains only the peak captured before exit
and labels that limited scope. Docker `OOMKilled` may still confirm OOM and an
otherwise unattributed exit 137 remains distinguishable. Every other terminal
state without ending cgroup evidence is rejected rather than classified.

No observation emits a memory-limit proposal. `memory.peak` is a measured
maximum for that cgroup lifetime, but neither Docker nor the kernel defines a
universal safety margin that turns it into a safe hard limit. A future limit
requires an accepted representative workload/capacity envelope and a separate
decision that names the workload, concurrency, host capacity, observation
window, zero-OOM acceptance, and rollback procedure. Disabling the OOM killer
is prohibited.

## Consequences

- Operators must capture evidence before recreating a failed worker.
- A healthy idle sample proves only that the sampled window had no new local
  pressure events; it is not capacity acceptance.
- Canonical Compose remains unchanged until representative workload evidence
  supports a bounded configuration.

## References

Docker, Inc. (2026a). *Define services in Docker Compose*. https://docs.docker.com/reference/compose-file/services/

Docker, Inc. (2026b). *Resource constraints*. https://docs.docker.com/engine/containers/resource_constraints/

The Linux Kernel Organization. (2026). *Control group v2*. https://docs.kernel.org/admin-guide/cgroup-v2.html
