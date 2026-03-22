"""CLI entry point for vLLM service."""

import argparse
import asyncio
import os
import sys
from typing import Optional

import uvicorn

from vllm_service import __version__
from vllm_service.config import settings
from vllm_service.utils import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="vLLM Service - OpenAI-compatible API server with Data Parallel support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start single node server
  vllm-service serve --model Qwen/Qwen2.5-7B-Instruct

  # Start Data Parallel rank 0 (coordinator node)
  vllm-service serve --model Qwen/Qwen2.5-7B-Instruct \\
      --data-parallel-size 2 --data-parallel-rank 0 \\
      --data-parallel-address 10.0.0.1

  # Start Data Parallel rank 1 (worker node)
  vllm-service serve --model Qwen/Qwen2.5-7B-Instruct \\
      --data-parallel-size 2 --data-parallel-rank 1 \\
      --data-parallel-address 10.0.0.1 --headless
        """,
    )
    
    # Model arguments
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name or path (default: from config)",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default=None,
        choices=["auto", "half", "float16", "bfloat16", "float32"],
        help="Data type for model weights",
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=None,
        help="Maximum context length",
    )
    parser.add_argument(
        "--gpu-memory-utilization",
        type=float,
        default=None,
        help="GPU memory utilization (0-1)",
    )
    
    # Server arguments
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind server to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind server to",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for authentication",
    )
    
    # Data Parallel arguments
    parser.add_argument(
        "--data-parallel-size",
        type=int,
        default=None,
        help="Total number of data parallel ranks",
    )
    parser.add_argument(
        "--data-parallel-rank",
        type=int,
        default=None,
        help="Rank of this node (0-indexed)",
    )
    parser.add_argument(
        "--data-parallel-address",
        type=str,
        default=None,
        help="Address of the coordinator node (rank 0)",
    )
    parser.add_argument(
        "--data-parallel-rpc-port",
        type=int,
        default=None,
        help="RPC port for data parallel coordination",
    )
    parser.add_argument(
        "--data-parallel-size-local",
        type=int,
        default=None,
        help="Number of local data parallel ranks on this node",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (for non-rank-0 nodes)",
    )
    
    # Engine arguments
    parser.add_argument(
        "--tensor-parallel-size",
        type=int,
        default=None,
        help="Tensor parallel size",
    )
    parser.add_argument(
        "--max-num-seqs",
        type=int,
        default=None,
        help="Maximum number of sequences per batch",
    )
    
    # Other
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"vLLM Service {__version__}",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    
    return parser.parse_args()


def update_settings_from_args(args: argparse.Namespace) -> None:
    """Update settings from command line arguments."""
    if args.model is not None:
        os.environ["VLLM_MODEL_NAME"] = args.model
    if args.dtype is not None:
        os.environ["VLLM_MODEL_DTYPE"] = args.dtype
    if args.max_model_len is not None:
        os.environ["VLLM_MAX_MODEL_LEN"] = str(args.max_model_len)
    if args.gpu_memory_utilization is not None:
        os.environ["VLLM_GPU_MEMORY_UTILIZATION"] = str(args.gpu_memory_utilization)
    
    if args.host is not None:
        os.environ["VLLM_HOST"] = args.host
    if args.port is not None:
        os.environ["VLLM_PORT"] = str(args.port)
    if args.api_key is not None:
        os.environ["VLLM_API_KEY"] = args.api_key
    
    if args.data_parallel_size is not None:
        os.environ["VLLM_DATA_PARALLEL_SIZE"] = str(args.data_parallel_size)
    if args.data_parallel_rank is not None:
        os.environ["VLLM_DATA_PARALLEL_RANK"] = str(args.data_parallel_rank)
    if args.data_parallel_address is not None:
        os.environ["VLLM_DATA_PARALLEL_ADDRESS"] = args.data_parallel_address
    if args.data_parallel_rpc_port is not None:
        os.environ["VLLM_DATA_PARALLEL_RPC_PORT"] = str(args.data_parallel_rpc_port)
    if args.data_parallel_size_local is not None:
        os.environ["VLLM_DATA_PARALLEL_SIZE_LOCAL"] = str(args.data_parallel_size_local)
    
    if args.tensor_parallel_size is not None:
        os.environ["VLLM_TENSOR_PARALLEL_SIZE"] = str(args.tensor_parallel_size)
    if args.max_num_seqs is not None:
        os.environ["VLLM_MAX_NUM_SEQS"] = str(args.max_num_seqs)


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    update_settings_from_args(args)
    
    from vllm_service.server.app import create_app
    
    host = os.environ.get("VLLM_HOST", "localhost")
    port = int(os.environ("VLLM_PORT", 8000))
    log_level = args.log_level.lower()
    
    logger.info(f"Starting vLLM Service v{__version__}")
    logger.info(f"Model: {settings.model.get('model_name', 'not set')}")
    logger.info(f"Host: {host}:{port}")
    
    dp_size = int(settings.data_parallel.get("data_parallel_size", 1))
    dp_rank = int(settings.data_parallel.get("data_parallel_rank", 0))
    if dp_size > 1:
        logger.info(f"Data Parallel: size={dp_size}, rank={dp_rank}")
        logger.info(f"Coordinator: {settings.data_parallel.get('data_parallel_address', 'localhost')}")
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
