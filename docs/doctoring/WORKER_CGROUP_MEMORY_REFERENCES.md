# Worker cgroup memory references

This supporting register documents the evidence boundary adopted by ADR 0247.
Docker Compose defines `mem_limit` as a hard allocation limit and
`mem_reservation` as a reservation. Docker Engine documents that the kernel
kills container processes on OOM by default and warns against disabling that
behavior without a hard memory limit. Linux cgroup v2 defines `memory.peak` as
the maximum observed usage and `memory.events.local` as the non-hierarchical
counter source; `oom_kill` counts processes killed by an OOM killer.

These contracts do not specify a universal multiplier or percentage for
turning one observed peak into a safe service limit. LineageWeave therefore
records measured evidence and leaves the limit unset until a representative
capacity acceptance is approved.

## References — APA 7th

Docker, Inc. (2026a). *Define services in Docker Compose*. https://docs.docker.com/reference/compose-file/services/

Docker, Inc. (2026b). *Resource constraints*. https://docs.docker.com/engine/containers/resource_constraints/

The Linux Kernel Organization. (2026). *Control group v2*. https://docs.kernel.org/admin-guide/cgroup-v2.html
