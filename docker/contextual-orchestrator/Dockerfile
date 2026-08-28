FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

WORKDIR /app

# Reuse the upstream implementation without copying it into LineageWeave.
# Pin the runtime to a reviewed immutable upstream commit; model selection,
# structured synthesis, and reasoning policy stay in contextual-orchestrator.
ADD --checksum=sha256:1049b781b72f5c7dcb13637717b79fba5736f8280ef74a8871b83d0f66e3ab7a https://github.com/ContextualWisdomLab/contextual-orchestrator/archive/4dbf04c267457d6caabadb1c62748368cf552088.tar.gz /tmp/contextual-orchestrator.tar.gz
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
