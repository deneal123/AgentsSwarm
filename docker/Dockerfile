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

# pyairports is sdist-only (no wheel on PyPI); install it explicitly into the venv.
# VIRTUAL_ENV is required: without it uv pip may resolve to a different environment.
RUN VIRTUAL_ENV=/app/.venv uv pip install --no-deps "pyairports==0.0.1" && \
    ls /app/.venv/lib/python3.12/site-packages/ | grep pyair && \
    /app/.venv/bin/python -c "import pyairports; print('pyairports OK:', pyairports.__file__)"

COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
    CMD curl -f http://localhost:${VLLM_PORT:-8000}/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
