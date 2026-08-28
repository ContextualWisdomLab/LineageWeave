FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf AS token-builder
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
       sh -s -- -y --profile minimal --default-toolchain 1.97.1
ENV PATH=/root/.cargo/bin:$PATH
ADD https://github.com/ContextualWisdomLab/contextual-orchestrator/archive/4dbf04c267457d6caabadb1c62748368cf552088.tar.gz /tmp/contextual-orchestrator.tar.gz
RUN mkdir /tmp/contextual-orchestrator \
    && tar -xzf /tmp/contextual-orchestrator.tar.gz --strip-components=1 -C /tmp/contextual-orchestrator \
    && python -m pip install --no-cache-dir 'maturin>=1.8,<2' \
    && maturin build --locked --release --manifest-path /tmp/contextual-orchestrator/rust/token_counter/Cargo.toml --out /tmp/token-wheels

FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

LABEL org.opencontainers.image.source="https://github.com/ContextualWisdomLab/contextual-orchestrator" \
      org.opencontainers.image.revision="4dbf04c267457d6caabadb1c62748368cf552088"

WORKDIR /app

# Reuse the upstream implementation without copying it into LineageWeave.
# Pin the runtime to a reviewed immutable upstream commit; model selection,
# structured synthesis, and reasoning policy stay in contextual-orchestrator.
ADD https://github.com/ContextualWisdomLab/contextual-orchestrator/archive/4dbf04c267457d6caabadb1c62748368cf552088.tar.gz /tmp/contextual-orchestrator.tar.gz
RUN mkdir /tmp/contextual-orchestrator \
    && tar -xzf /tmp/contextual-orchestrator.tar.gz --strip-components=1 -C /tmp/contextual-orchestrator \
    && cp -R /tmp/contextual-orchestrator/contextual_orchestrator /app/contextual_orchestrator \
    && cp -R /tmp/contextual-orchestrator/examples /app/examples \
    && python -m pip install --no-cache-dir 'uv==0.12.6' \
    && cd /tmp/contextual-orchestrator \
    && uv export --locked --no-dev --no-emit-project --extra queue --no-hashes --output-file /tmp/runtime-requirements.txt \
    && python -m pip install --no-cache-dir --requirement /tmp/runtime-requirements.txt \
    && python -c 'import cryptography, jsonschema, redis; from opentelemetry.exporter.otlp.proto.http import trace_exporter' \
    && rm -rf /tmp/contextual-orchestrator /tmp/contextual-orchestrator.tar.gz /tmp/runtime-requirements.txt \
    && useradd --uid 10001 --no-create-home orchestrator

COPY --from=token-builder /tmp/token-wheels /tmp/token-wheels
RUN pip install --no-cache-dir /tmp/token-wheels/*.whl \
    && cp /usr/local/lib/python3.12/site-packages/contextual_orchestrator/_token_packer*.so /app/contextual_orchestrator/ \
    && rm -rf /tmp/token-wheels

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
