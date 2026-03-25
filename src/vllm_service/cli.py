"""CLI entry point for vLLM service."""

import argparse
import logging
import os
import sys
import socket
import signal
from typing import Optional

import uvicorn

from vllm_service import __version__
from vllm_service.config import settings


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

    # Create a parent parser that holds all options for the `serve` command.
    # This makes options available after the subcommand (e.g. `serve --model ...`).
    parent = argparse.ArgumentParser(add_help=False)

    # Model arguments
    parent.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name or path (default: from config)",
    )
    parent.add_argument(
        "--dtype",
        type=str,
        default=None,
        choices=["auto", "half", "float16", "bfloat16", "float32"],
        help="Data type for model weights",
    )
    parent.add_argument(
        "--max-model-len",
        type=int,
        default=None,
        help="Maximum context length",
    )
    parent.add_argument(
        "--gpu-memory-utilization",
        type=float,
        default=None,
        help="GPU memory utilization (0-1)",
    )

    # Server arguments
    parent.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind server to",
    )
    parent.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind server to",
    )
    parent.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for authentication",
    )

    # Data Parallel arguments
    parent.add_argument(
        "--data-parallel-size",
        type=int,
        default=None,
        help="Total number of data parallel ranks",
    )
    parent.add_argument(
        "--data-parallel-rank",
        type=int,
        default=None,
        help="Rank of this node (0-indexed)",
    )
    parent.add_argument(
        "--data-parallel-address",
        type=str,
        default=None,
        help="Address of the coordinator node (rank 0)",
    )
    parent.add_argument(
        "--data-parallel-rpc-port",
        type=int,
        default=None,
        help="RPC port for data parallel coordination",
    )
    parent.add_argument(
        "--data-parallel-size-local",
        type=int,
        default=None,
        help="Number of local data parallel ranks on this node",
    )
    parent.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (for non-rank-0 nodes)",
    )

    # Engine arguments
    parent.add_argument(
        "--tensor-parallel-size",
        type=int,
        default=None,
        help="Tensor parallel size",
    )
    parent.add_argument(
        "--max-num-seqs",
        type=int,
        default=None,
        help="Maximum number of sequences per batch",
    )

    # Other
    parent.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )
    parent.add_argument(
        "--version",
        action="version",
        version=f"vLLM Service {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Attach the parent parser to the `serve` subcommand so that its options are
    # valid after the subcommand token (e.g. `serve --model ...`).
    serve_parser = subparsers.add_parser("serve", parents=[parent], help="Start the API server")
    
    return parser.parse_args()


def update_settings_from_args(args: argparse.Namespace) -> None:
    """Update settings from command line arguments."""
    # Model settings are stored in structured settings model section.
    if args.model is not None:
        settings.set("MODEL.model_name", args.model)
    if args.dtype is not None:
        settings.set("MODEL.model_dtype", args.dtype)
    if args.max_model_len is not None:
        settings.set("MODEL.max_model_len", int(args.max_model_len))
    if args.gpu_memory_utilization is not None:
        settings.set("MODEL.gpu_memory_utilization", float(args.gpu_memory_utilization))
 
    if args.host is not None:
        # Use local variable in main, do not override VLLM_HOST globally to avoid vLLM engine networking conflicts.
        settings.set("host", args.host)
    if args.port is not None:
        settings.set("port", int(args.port))
    if args.api_key is not None:
        os.environ["VLLM_API_KEY"] = args.api_key
 
    # Data Parallel arguments: keep in environment and structured settings.
    if args.data_parallel_size is not None:
        os.environ["VLLM_DATA_PARALLEL_SIZE"] = str(args.data_parallel_size)
        settings.set("DATA_PARALLEL.data_parallel_size", args.data_parallel_size)
    if args.data_parallel_rank is not None:
        os.environ["VLLM_DATA_PARALLEL_RANK"] = str(args.data_parallel_rank)
        settings.set("DATA_PARALLEL.data_parallel_rank", args.data_parallel_rank)
    if args.data_parallel_address is not None:
        os.environ["VLLM_DATA_PARALLEL_ADDRESS"] = args.data_parallel_address
        settings.set("DATA_PARALLEL.data_parallel_address", args.data_parallel_address)
    if args.data_parallel_rpc_port is not None:
        os.environ["VLLM_DATA_PARALLEL_RPC_PORT"] = str(args.data_parallel_rpc_port)
        settings.set("DATA_PARALLEL.data_parallel_rpc_port", args.data_parallel_rpc_port)
    if args.data_parallel_size_local is not None:
        os.environ["VLLM_DATA_PARALLEL_SIZE_LOCAL"] = str(args.data_parallel_size_local)
        settings.set("DATA_PARALLEL.data_parallel_size_local", args.data_parallel_size_local)
 
    if args.tensor_parallel_size is not None:
        settings.set("ENGINE.tensor_parallel_size", int(args.tensor_parallel_size))
    if args.max_num_seqs is not None:
        settings.set("ENGINE.max_num_seqs", int(args.max_num_seqs))


def _find_available_port(host: str, start_port: int, max_tries: int = 100) -> int:
    """Find the first available port starting from start_port."""
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"No available ports in range {start_port}-{start_port + max_tries - 1}."
    )


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Update settings from args
    update_settings_from_args(args)

    # Import here to avoid circular imports
    from vllm_service.server.app import create_app
    
    # Get configuration
    host = args.host or os.environ.get("VLLM_HOST", settings.get("host", "0.0.0.0"))
    preferred_port = int(args.port or os.environ.get("VLLM_PORT", settings.get("port", 8000)))
    try:
        port = _find_available_port(host, preferred_port, max_tries=100)
    except RuntimeError as e:
        logger.error("Could not find available port: %s", e)
        sys.exit(1)
    
    if port != preferred_port:
        logger.warning(
            "Preferred port %d is unavailable, using fallback port %d.",
            preferred_port,
            port,
        )
        os.environ["VLLM_PORT"] = str(port)
    else:
        logger.info("Using port %d", port)
    log_level = args.log_level.lower()
    
    logger.info(f"Starting vLLM Service v{__version__}")
    model_name = os.environ.get("VLLM_MODEL_NAME", settings.get("MODEL.model_name", settings.get("model_name", "not set")))
    logger.info(f"Model: {model_name}")
    logger.info(f"Host: {host}:{port}")
    
    # Data Parallel info
    dp_size = int(os.environ.get("VLLM_DATA_PARALLEL_SIZE", settings.get("DATA_PARALLEL.data_parallel_size", settings.get("data_parallel_size", 1))))
    dp_rank = int(os.environ.get("VLLM_DATA_PARALLEL_RANK", settings.get("DATA_PARALLEL.data_parallel_rank", settings.get("data_parallel_rank", 0))))
    if dp_size > 1:
        logger.info(f"Data Parallel: size={dp_size}, rank={dp_rank}")
        logger.info(f"Coordinator: {settings.get('DATA_PARALLEL.data_parallel_address', 'localhost')}")
    
    # Create and run app
    app = create_app()
 
    # Fail fast if host/port are already in use.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
    except OSError as e:
        logging.getLogger(__name__).warning(
            "Port %s is unexpectedly unavailable on host %s (race condition): %s. Continuing.",
            port,
            host,
            e,
        )
 
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            lifespan="on",
        )
    except Exception as exc:
        logger.error("Server run exception: %s", exc)
        sys.exit(1)
 
 
if __name__ == "__main__":
    main()
