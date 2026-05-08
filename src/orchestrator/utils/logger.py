import logging
import sys
from datetime import datetime

from orchestrator.config import PROJECT_ROOT

_root_configured = False
_ROOT_LOGGER_NAME = "orchestrator"


def _configure_root_logger() -> None:
    """Configure the root 'orchestrator' logger once per process."""
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(console)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(log_dir / f"orchestrator_{timestamp}.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers.
    for noisy in ("urllib3", "asyncio", "httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger that inherits from the root orchestrator logger.

    Each module should call ``get_logger(__name__)`` at import time.
    All loggers share the same handlers configured on the 'orchestrator' root.
    """
    _configure_root_logger()
    return logging.getLogger(name)
