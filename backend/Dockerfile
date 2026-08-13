FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
WORKDIR /app

# rankweave and fast-mlsirm install from a git URL (see pyproject.toml) --
# neither has a PyPI release yet. fast-mlsirm additionally ships a
# PyO3/maturin Rust core with no fallback wheel (ADR 0003), so this build
# needs a real Rust toolchain, not just Python -- build-essential supplies
# the C linker maturin needs on Linux. Create the runtime user here so the
# later USER instruction is not a no-op against a missing account
# (DS-0002: explicit non-root USER).
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

# Pinned, non-interactive rustup install (minimal profile: no docs/clippy,
# just rustc+cargo) -- same "pinned, reproducible install" discipline this
# project already applies to rankweave/fast-mlsirm's own commit pins.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain 1.97.1
ENV PATH="/root/.cargo/bin:${PATH}"

COPY pyproject.toml ./
COPY lineageweave ./lineageweave
COPY backend ./backend

RUN pip install --no-cache-dir ".[backend]" \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
