# Orchestrator service container
# Usage (dev): docker compose -f docker-compose.dev.yml up --build

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install system deps for uv and build
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends curl build-essential \ 
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy dependency manifests (README.md required by hatchling at build time)
COPY pyproject.toml uv.lock README.md ./

# Create virtualenv and install deps
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv sync --frozen

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code (dev compose overrides with bind mount)
COPY src ./src

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "orchestrator.app:app", "--host", "0.0.0.0", "--port", "8000"]
