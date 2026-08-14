FROM node:24.18.0-alpine AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run coverage && npm run build

FROM ghcr.io/astral-sh/uv:0.9.27-python3.13-bookworm-slim
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
