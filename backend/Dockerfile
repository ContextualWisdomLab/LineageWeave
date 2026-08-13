FROM python:3.12-slim
WORKDIR /app

# rankweave installs from a git URL (see pyproject.toml) -- no PyPI release yet.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY lineageweave ./lineageweave
COPY backend ./backend

RUN pip install --no-cache-dir ".[backend]"

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
