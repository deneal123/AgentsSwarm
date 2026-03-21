"""FastAPI server module."""

from vllm_service.server.app import create_app, run_server

__all__ = ["create_app", "run_server"]
