import logging
import sys
from uuid import uuid4

from typing import Optional

from orchestrator.config import PROJECT_ROOT


def setup_logging(name: str) -> logging.Logger:
    log_dir = PROJECT_ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)
    root_logger = logging.getLogger(name)
    root_logger.setLevel(logging.DEBUG)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    file_handler = logging.FileHandler(f'{log_dir}/{uuid4().hex[:8]}.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    return root_logger


_logger: Optional[logging.Logger] = None


def get_logger(name: str) -> logging.Logger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logging(name)
    return _logger

