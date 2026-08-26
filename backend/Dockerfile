FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
ARG LINEAGEWEAVE_SOURCE_REVISION=unknown
LABEL org.opencontainers.image.revision=${LINEAGEWEAVE_SOURCE_REVISION}
WORKDIR /app

# Hash-pinned bootstrap input is copied before dependency installation so the
# build cannot resolve a different uv artifact for the same version.
COPY backend/uv-bootstrap-requirements.txt /tmp/uv-bootstrap-requirements.txt

# rankweave and fast-mlsirm install from immutable git commit references.
# fast-mlsirm builds a PyO3/maturin core, so the image needs a C linker and
# the repository-pinned Rust toolchain. The runtime user is created before
# dependencies so no application process runs as root.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser \
    && python -m pip install --no-cache-dir --no-deps \
        --require-hashes --only-binary=:all: \
        -r /tmp/uv-bootstrap-requirements.txt

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain 1.97.1
ENV PATH="/app/.venv/bin:/root/.cargo/bin:${PATH}" \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra backend --no-install-project --no-editable
COPY lineageweave ./lineageweave
COPY backend ./backend
COPY scripts/backfill_post_embeddings.py ./scripts/backfill_post_embeddings.py
# lineageweave/ontology.py resolves this path relative to itself
# (parents[1] = /app) -- ADR 0004.
COPY docs/ontology ./docs/ontology

# Install exactly the committed universal lock. --no-editable prevents a
# runtime dependency on source-tree editability while retaining package data.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra backend --no-editable \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
