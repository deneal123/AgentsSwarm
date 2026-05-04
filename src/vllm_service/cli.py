"""CLI entry point for vLLM service."""

import argparse
import logging
import os
import sys

import uvicorn

from vllm_service import __version__
from vllm_service.config import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="vLLM Service - OpenAI-compatible API server with Data Parallel support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single node
  vllm-service serve --model Qwen/Qwen2.5-7B-Instruct

  # Data Parallel rank 0 (coordinator)
  vllm-service serve --model Qwen/Qwen2.5-7B-Instruct \\
      --data-parallel-size 2 --data-parallel-rank 0 \\
      --data-parallel-address 10.0.0.1

  # Data Parallel rank 1 (worker)
  vllm-service serve --model Qwen/Qwen2.5-7B-Instruct \\
      --data-parallel-size 2 --data-parallel-rank 1 \\
      --data-parallel-address 10.0.0.1 --headless
        """,
    )

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--model", type=str, default=None)
    parent.add_argument(
        "--dtype",
        type=str,
        default=None,
        choices=["auto", "half", "float16", "bfloat16", "float32"],
    )
    parent.add_argument("--max-model-len", type=int, default=None)
    parent.add_argument("--gpu-memory-utilization", type=float, default=None)
    parent.add_argument("--host", type=str, default=None)
    parent.add_argument("--port", type=int, default=None)
    parent.add_argument("--api-key", type=str, default=None)
    parent.add_argument("--data-parallel-size", type=int, default=None)
    parent.add_argument("--data-parallel-rank", type=int, default=None)
    parent.add_argument("--data-parallel-address", type=str, default=None)
    parent.add_argument("--data-parallel-rpc-port", type=int, default=None)
    parent.add_argument("--data-parallel-size-local", type=int, default=None)
    parent.add_argument("--headless", action="store_true")
    parent.add_argument("--tensor-parallel-size", type=int, default=None)
    parent.add_argument("--max-num-seqs", type=int, default=None)
    parent.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parent.add_argument("--version", action="version", version=f"vLLM Service {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.add_parser("serve", parents=[parent], help="Start the API server")

    return parser.parse_args()


def _apply_args_to_settings(args: argparse.Namespace) -> None:
    if args.model is not None:
        settings.set("MODEL.model_name", args.model)
    if args.dtype is not None:
        settings.set("MODEL.model_dtype", args.dtype)
    if args.max_model_len is not None:
        settings.set("MODEL.max_model_len", int(args.max_model_len))
    if args.gpu_memory_utilization is not None:
        settings.set("MODEL.gpu_memory_utilization", float(args.gpu_memory_utilization))

    if args.host is not None:
        settings.set("host", args.host)
    if args.port is not None:
        settings.set("port", int(args.port))
    if args.api_key is not None:
        os.environ["VLLM_API_KEY"] = args.api_key

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


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    _apply_args_to_settings(args)

    # Deferred import: avoids loading vllm at CLI parse time.
    from vllm_service.server.app import create_app

    host = args.host or os.environ.get("VLLM_HOST", settings.get("host", "0.0.0.0"))
    port = int(args.port or os.environ.get("VLLM_PORT", settings.get("port", 8000)))

    logger.info("Starting vLLM Service v%s", __version__)
    logger.info(
        "Model: %s",
        os.environ.get("VLLM_MODEL_NAME", settings.get("MODEL.model_name", "not set")),
    )
    logger.info("Listening on %s:%d", host, port)

    dp_size = int(
        os.environ.get(
            "VLLM_DATA_PARALLEL_SIZE",
            settings.get("DATA_PARALLEL.data_parallel_size", 1),
        )
    )
    if dp_size > 1:
        dp_rank = int(
            os.environ.get(
                "VLLM_DATA_PARALLEL_RANK",
                settings.get("DATA_PARALLEL.data_parallel_rank", 0),
            )
        )
        logger.info("Data Parallel: size=%d, rank=%d", dp_size, dp_rank)
        logger.info(
            "Coordinator: %s",
            settings.get("DATA_PARALLEL.data_parallel_address", "localhost"),
        )

    app = create_app()

    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=args.log_level.lower(),
            lifespan="on",
        )
    except Exception as exc:
        logger.error("Server error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
