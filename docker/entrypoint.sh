#!/bin/bash
# docker/entrypoint.sh

set -e

echo "Starting vLLM Service..."
echo "DP Rank: ${VLLM_DATA_PARALLEL_RANK:-0}"
echo "DP Size: ${VLLM_DATA_PARALLEL_SIZE:-1}"

# Установка недостающей зависимости
uv pip install pyairports

if [ "${VLLM_DATA_PARALLEL_RANK}" = "0" ]; then
    echo "Starting as Coordinator (rank 0)"
    exec uv run python -m vllm_service serve
else
    echo "Starting as Worker (rank ${VLLM_DATA_PARALLEL_RANK})"
    exec uv run python -m vllm_service serve --headless
fi