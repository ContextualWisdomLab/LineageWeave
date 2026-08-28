FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

WORKDIR /app

# Reuse the upstream implementation without copying it into LineageWeave.
# Pin the runtime to a reviewed immutable upstream commit; model selection,
# structured synthesis, and reasoning policy stay in contextual-orchestrator.
ADD --checksum=sha256:243e3efa9a0c2a07cd02e4620c7a40fee8b8d9c04d7df394136ab60f2635a45d https://github.com/ContextualWisdomLab/contextual-orchestrator/archive/1a40e0f7ad10d1a24137d69d20e44fc9a5dcdd89.tar.gz /tmp/contextual-orchestrator.tar.gz
COPY requirements.lock /tmp/orchestrator-requirements.lock
RUN mkdir /tmp/contextual-orchestrator \
    && tar -xzf /tmp/contextual-orchestrator.tar.gz --strip-components=1 -C /tmp/contextual-orchestrator \
    && cp -R /tmp/contextual-orchestrator/contextual_orchestrator /app/contextual_orchestrator \
    && cp -R /tmp/contextual-orchestrator/examples /app/examples \
    && rm -rf /tmp/contextual-orchestrator /tmp/contextual-orchestrator.tar.gz \
    && python -m pip install --no-cache-dir --require-hashes \
        -r /tmp/orchestrator-requirements.lock \
    && rm /tmp/orchestrator-requirements.lock \
    && useradd --uid 10001 --no-create-home orchestrator

COPY agents.json /app/agents.json
COPY start.py /app/start.py

ENV AGENTS_FILE=/app/agents.json \
    PORT=8000

USER orchestrator
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["python", "/app/start.py"]
