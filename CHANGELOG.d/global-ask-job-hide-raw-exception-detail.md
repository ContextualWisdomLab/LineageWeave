# Unreleased — Global Ask job failure detail no longer leaks raw exceptions

## Fixed

- `process_global_ask_job`'s failure path stored the raw `str(exc)` in
  `failure_detail`, which `GET /api/ask/jobs/{id}` returns verbatim to
  the polling reader -- reintroducing the exception-leak issue (#361)
  the synchronous `/api/ask` endpoint had already been fixed against,
  just on the new async job path introduced when Global Ask moved
  behind the Valkey job queue. The full exception is still logged
  internally; the reader only ever sees a bounded, generic message.
