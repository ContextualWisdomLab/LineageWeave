FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
WORKDIR /app

# rankweave installs from a git URL (see pyproject.toml) -- no PyPI release yet.
# Create the runtime user here so the later USER instruction is not a
# no-op against a missing account (DS-0002: explicit non-root USER).
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

COPY pyproject.toml ./
COPY lineageweave ./lineageweave
COPY backend ./backend

RUN pip install --no-cache-dir ".[backend]" \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
