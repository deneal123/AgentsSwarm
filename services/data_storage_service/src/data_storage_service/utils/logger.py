"""Logging utilities for the service package.

Originally the codebase referenced ``service.utils.logger.get_logger`` in
several modules (tasks, ``pushi_service``).  The module had been removed at
some point which resulted in ``ModuleNotFoundError`` during application
startup.  The helper simply ensures the global logging configuration from
settings is applied (so callers can import it anywhere) and then returns a
standard ``logging.Logger`` instance.

The configuration is applied lazily at import time so that every module that
requests a logger will see the same settings.  ``service.main`` also applies
logging configuration but importing this helper earlier (for Celery tasks,
etc.) won't break anything.
"""

from __future__ import annotations

import logging
import logging.config

from service.settings import LOGGING

# Apply global logging configuration when module is imported.  This mirrors
# the configuration step performed in ``service.main`` so that loggers are
# immediately usable even in modules that are imported before the FastAPI
# application has been created (e.g. Celery tasks or background jobs).
logging.config.dictConfig(LOGGING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name.

    The returned logger will already have handlers/formatters configured by
    ``LOGGING``.  Simply a small wrapper around ``logging.getLogger`` so that
    callers do not have to import ``logging`` themselves when they only need a
    single logger instance.
    """

    return logging.getLogger(name)
