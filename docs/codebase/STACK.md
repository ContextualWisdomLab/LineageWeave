# Stack

## Observed

- Python 3.10+ is managed with `uv`; runtime dependencies are `psycopg[binary]` and `truststore`.
- The API and analysis runtime are `lineageweave.py` and `lineageweave_server.py`.
- The browser surface is React 19/Vite 7 under `web/`; `web/src/App.jsx` calls the HTTP API.
- PostgreSQL is the system of record. Valkey Streams carry committed outbox events.
- Compose supplies the product container, Valkey, and a model-task HTTP stand-in.
- Tests use pytest and coverage; the current complete source gate passed all
  355 tests at 100% line-and-branch coverage across four product-runtime
  modules plus one retained test-boundary utility (7,627 statements and 2,984
  branches). The shipped product-runtime subset is 7,473 statements and 2,940
  branches. A process-owned PostgreSQL test database keeps runtime advisory
  locks and analysis writes isolated.
- Report psychometrics stays behind the separate fast-mlsirm HTTP/local
  boundary. The local runtime check used its installed Rust-backed EAP path;
  LineageWeave does not copy that implementation into the product.

## Evidence

- `pyproject.toml`, `web/package.json`, `compose.yaml`
- `uv run pytest -q`
- `uv run coverage run --branch ... -m pytest -q && uv run coverage report --fail-under=100`
- `cd web && npm run build`

## Boundary

TEPP and fast-mlsirm remain separate software. LineageWeave calls them only
through explicit HTTP or local-process adapter contracts; no upstream internals
are imported or copied into the product.
