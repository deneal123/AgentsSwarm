"""CLI entrypoints for running the Orchestrator service."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
	"""Launch the FastAPI app with uvicorn.

	This keeps configuration tiny for now; Docker/K8s can override host/port
	via environment variables.
	"""

	host = os.getenv("HOST", "0.0.0.0")
	port = int(os.getenv("PORT", "8000"))
	uvicorn.run("orchestrator.app:app", host=host, port=port, reload=os.getenv("RELOAD") == "1")


if __name__ == "__main__":
	main()
