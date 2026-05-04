FROM nvidia/cuda:12.1.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TORCH_CUDA_ARCH_LIST="7.0" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (separate layer for Docker cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY src ./src
COPY README.md ./
RUN uv sync --frozen --no-dev

# pyairports-0.0.1 on PyPI is a broken sdist: the archive ships 'sample/' instead of
# 'pyairports/', so the dist-info is created but the actual package is never installed.
# Create the package directly in the venv so the outlines import succeeds at startup.
RUN mkdir -p /app/.venv/lib/python3.12/site-packages/pyairports && \
    printf 'AIRPORT_LIST = []\n' \
        > /app/.venv/lib/python3.12/site-packages/pyairports/airports.py && \
    touch /app/.venv/lib/python3.12/site-packages/pyairports/__init__.py && \
    /app/.venv/bin/python -c "from pyairports.airports import AIRPORT_LIST; print('pyairports OK')"

COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
    CMD curl -f http://localhost:${VLLM_PORT:-8000}/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
