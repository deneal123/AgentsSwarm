#!/bin/bash
set -e

echo "Starting vLLM Service..."
echo "DP Rank: ${VLLM_DATA_PARALLEL_RANK:-0}"
echo "DP Size: ${VLLM_DATA_PARALLEL_SIZE:-1}"

PYTHON=/app/.venv/bin/python

if [ "${VLLM_DATA_PARALLEL_RANK:-0}" = "0" ]; then
    echo "Starting as Coordinator (rank 0)"
    exec "$PYTHON" -m vllm_service serve
else
    echo "Starting as Worker (rank ${VLLM_DATA_PARALLEL_RANK})"
    exec "$PYTHON" -m vllm_service serve --headless
fi
