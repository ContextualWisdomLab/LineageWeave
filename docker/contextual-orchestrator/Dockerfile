# Immutable upstream source; no copied or patched orchestration implementation.
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf AS source
ADD https://codeload.github.com/ContextualWisdomLab/contextual-orchestrator/tar.gz/8e1f1a8bf3e96e56dc8fcc90ec777883a1d56ce6 /tmp/source.tar.gz
RUN python -c "import hashlib; assert hashlib.sha256(open('/tmp/source.tar.gz','rb').read()).hexdigest() == '2172a88dc1a9e9458417f0a0b76dac8760b715d0e4f3b9a6caa8d4b46221da68'" \
    && mkdir /source && tar -xzf /tmp/source.tar.gz --strip-components=1 -C /source

FROM ghcr.io/pyo3/maturin@sha256:b6c8b59a0170b77eb31a35b56034abd39972483ad0ebfff344deaa42a85f3bd3 AS maturin-tools
FROM rust:1.97.1-slim-bookworm@sha256:2775a09d208ff0d7c1f50490c45b62db929e87ba1dcbc3f2132ac71a704bcdd3 AS dependency-builder
RUN apt-get update && apt-get install --no-install-recommends --yes build-essential && rm -rf /var/lib/apt/lists/*
COPY --from=maturin-tools /usr/local/bin/uv /usr/local/bin/uv
COPY --from=maturin-tools /usr/bin/maturin /usr/local/bin/maturin
COPY --from=source /source /build
RUN uv python install 3.12 \
    && printf 'maturin==1.15.0 --hash=sha256:0ebf9767892725083138e671c34482c660317a2f3d6a29fc0e0f34e9d8c99136\n' > /build/native-build.lock \
    && uv pip install --python 3.12 --target /build/native-tools --require-hashes --only-binary :all: --no-deps -r /build/native-build.lock \
    && uv export --project /build --frozen --no-dev --extra api --extra db --extra queue --no-emit-project -o /build/runtime-export.lock \
    && uv pip install --python 3.12 --require-hashes --only-binary :all: -r /build/runtime-export.lock --target /build/deps \
    && PYO3_PYTHON=$(uv python find 3.12) /build/native-tools/bin/maturin build --locked --release --manifest-path /build/rust/token_counter/Cargo.toml --out /build/wheels \
    && PYO3_PYTHON=$(uv python find 3.12) /build/native-tools/bin/maturin build --locked --release --manifest-path /build/rust/decision_receipt/Cargo.toml --out /build/wheels \
    && uv pip install --python 3.12 --no-deps /build/wheels/*.whl --target /build/deps

FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf
WORKDIR /app
COPY --from=dependency-builder /build/deps/ /usr/local/lib/python3.12/site-packages/
COPY --from=source /source/contextual_orchestrator/ /usr/local/lib/python3.12/site-packages/contextual_orchestrator/
COPY --from=source /source/examples/ /app/examples/
COPY --from=source /source/requirements.lock /source/uv.lock /source/pyproject.toml /app/upstream/
COPY --from=source /source/rust/Cargo.lock /app/upstream/Cargo.lock
COPY --from=dependency-builder /build/runtime-export.lock /build/native-build.lock /app/upstream/
COPY agents.json /app/agents.json
COPY start.py /app/start.py
RUN useradd --uid 10001 --create-home orchestrator
ENV AGENTS_FILE=/app/agents.json PORT=8000
LABEL org.opencontainers.image.revision="8e1f1a8bf3e96e56dc8fcc90ec777883a1d56ce6"
USER orchestrator
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["python", "/app/start.py"]
