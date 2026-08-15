FROM node:24.18.0-alpine@sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN chown -R node:node /build
USER node
RUN npm ci
COPY --chown=node:node web/ ./
RUN npm run coverage && npm run build

FROM ghcr.io/astral-sh/uv:0.9.27-python3.13-bookworm-slim@sha256:fb12b20e86027dac1b4c78a359ba091b639df39b85d9e9f5d93a91bd08e01666
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY lineageweave.py lineageweave_embeddings.py lineageweave_server.py ./
COPY --from=web-build /build/web/dist ./web/dist
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin lineageweave \
    && chown -R lineageweave:lineageweave /app
USER lineageweave
EXPOSE 8000
CMD ["python", "lineageweave_server.py"]
