# Worker memory evidence procedure

Run this before restarting or recreating a worker, over a declared window that
contains the workload and concurrency being accepted:

```bash
uv run python scripts/capture_worker_memory_evidence.py \
  --sample-seconds "$OBSERVATION_SECONDS" \
  --output /tmp/lineageweave-worker-memory-evidence.json
```

The output contains aggregates and no container identifier or record content.
Preserve it outside git with the workload definition and host capacity. An
`oom_confirmed` result requires Docker `OOMKilled` or a local kernel
`oom_kill` delta. `sigkill_unattributed` requires further host/runtime logs;
do not relabel it OOM. A container change invalidates the window.

Acceptance requires the declared representative workload to finish on one
unchanged container with zero `high`, `max`, `oom`, and `oom_kill` deltas.
The observed peak is evidence, not a proposed Compose limit. Any future
`mem_limit`/`mem_reservation` change needs a separate ADR and rollback test.
