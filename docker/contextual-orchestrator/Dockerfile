# Build the exact Rust token-packer shipped by the pinned upstream archive.
# The native module is mandatory: token budgets, vector reductions, and RMSE
# fail closed rather than falling back to Python arithmetic.
ARG MATURIN_BUILDER_IMAGE=ghcr.io/pyo3/maturin@sha256:b6c8b59a0170b77eb31a35b56034abd39972483ad0ebfff344deaa42a85f3bd3
FROM ${MATURIN_BUILDER_IMAGE} AS token-builder

ADD --checksum=sha256:cc7cb6b693c40713046d55aea40a37dd9c42225f4bc8539806faed45d2ff8b55 https://github.com/ContextualWisdomLab/contextual-orchestrator/archive/18c108be6b884b051198f33c903b1ee6eeed405f.tar.gz /tmp/contextual-orchestrator.tar.gz
RUN mkdir -p /build/contextual-orchestrator \
    && tar -xzf /tmp/contextual-orchestrator.tar.gz --strip-components=1 \
        -C /build/contextual-orchestrator \
    && rm /tmp/contextual-orchestrator.tar.gz
WORKDIR /build/contextual-orchestrator/rust/token_counter
RUN maturin build --locked --release --out /build/wheels \
    && set -- /build/wheels/*.whl \
    && test "$#" -eq 1 \
    && test -f "$1"

FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

WORKDIR /app

ARG CONTEXTUAL_ORCHESTRATOR_SOURCE_REVISION=unknown
LABEL org.opencontainers.image.revision=${CONTEXTUAL_ORCHESTRATOR_SOURCE_REVISION}

# Reuse the upstream implementation without copying it into LineageWeave.
# Pin the runtime to a reviewed immutable upstream commit; model selection,
# structured synthesis, and reasoning policy stay in contextual-orchestrator.
COPY requirements.lock /tmp/orchestrator-requirements.lock
COPY --from=token-builder /build/contextual-orchestrator/contextual_orchestrator /app/contextual_orchestrator
COPY --from=token-builder /build/contextual-orchestrator/examples /app/examples
COPY --from=token-builder /build/wheels /tmp/token-wheels
RUN python -m pip install --no-cache-dir --require-hashes \
        -r /tmp/orchestrator-requirements.lock \
    && rm /tmp/orchestrator-requirements.lock \
    && set -- /tmp/token-wheels/*.whl \
    && test "$#" -eq 1 \
    && test -f "$1" \
    && python -m pip install --no-cache-dir --no-deps "$1" \
    && cp /usr/local/lib/python3.12/site-packages/contextual_orchestrator/_token_packer*.so /app/contextual_orchestrator/ \
    && rm -rf /tmp/token-wheels \
    && useradd --uid 10001 --no-create-home orchestrator

COPY agents.json /app/agents.json
COPY start.py /app/start.py
COPY verify_startup_contract.py /app/verify_startup_contract.py
RUN python /app/verify_startup_contract.py \
    && rm /app/verify_startup_contract.py

ENV AGENTS_FILE=/app/agents.json \
    PORT=8000

USER orchestrator
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["python", "/app/start.py"]
