"""Pytest конфигурация и общие фикстуры для robot_edge тестов."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from nvidia_isaac_simulation.utils import logger

import pytest

try:
    import isaacsim
    logger.info("Isaac Sim успешно импортирован.")
except ImportError:
    raise ImportError("Isaac Sim не найден. Убедитесь, что он установлен и доступен в PYTHONPATH.")


