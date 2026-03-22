"""Pytest конфигурация и общие фикстуры для orchestrator тестов."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from orchestrator.utils import get_logger

import pytest

logger = get_logger(__name__)

