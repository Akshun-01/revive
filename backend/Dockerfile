# Revive backend image. Runs FastAPI + FastMCP via the Windows-safe serve entrypoint
# (on Linux the selector loop is the default, so psycopg async works out of the box).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    REVIVE_HOST=0.0.0.0 \
    REVIVE_PORT=8000

WORKDIR /app

RUN pip install --no-cache-dir uv

# Project metadata + source (the package build needs app/ and README.md).
COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY scripts ./scripts

# Install runtime deps + the db extra (Postgres checkpointer, SQLAlchemy, cryptography).
RUN uv sync --no-dev --extra db

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "scripts.serve"]
