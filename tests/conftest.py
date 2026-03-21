"""Pytest конфигурация и общие фикстуры для robot_edge тестов."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Env для Settings ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def set_robot_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Устанавливает обязательный ROBOT_ID для всех тестов."""
    monkeypatch.setenv("ROBOT_ID", "test-robot-01")


@pytest.fixture
def settings():
    """Свежий экземпляр Settings (без lru_cache)."""
    from robot_edge.config import Settings
    return Settings()


# ─── Mock MQTT клиент ─────────────────────────────────────────────────────────

class MockMQTTClient:
    """Минимальный мок paho mqtt.Client."""

    def __init__(self) -> None:
        self.published: list[dict[str, Any]] = []
        self.connected = True
        self.on_message: Any = None
        self.on_connect: Any = None
        self.on_disconnect: Any = None

    def publish(self, topic: str, payload: bytes, qos: int = 0, retain: bool = False) -> MagicMock:
        self.published.append({"topic": topic, "payload": payload, "qos": qos})
        result = MagicMock()
        result.rc = 0
        return result

    def subscribe(self, topic: str, qos: int = 0) -> None:
        pass

    def is_connected(self) -> bool:
        return self.connected

    def loop_start(self) -> None:
        pass

    def loop_stop(self) -> None:
        pass

    def disconnect(self) -> None:
        self.connected = False

    def inject_message(self, topic: str, payload: bytes) -> None:
        """Имитировать входящее MQTT сообщение."""
        if self.on_message:
            msg = MagicMock()
            msg.topic = topic
            msg.payload = payload
            self.on_message(self, None, msg)


@pytest.fixture
def mqtt_client() -> MockMQTTClient:
    return MockMQTTClient()


# ─── Asyncio event loop ───────────────────────────────────────────────────────

@pytest.fixture
def event_loop():
    """Создать новый event loop для каждого теста."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Примеры сообщений ────────────────────────────────────────────────────────

@pytest.fixture
def sample_twist_dict() -> dict[str, Any]:
    return {
        "linear": {"x": 0.5, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": 0.3},
    }


@pytest.fixture
def sample_odom_dict() -> dict[str, Any]:
    return {
        "pose": {
            "pose": {
                "position": {"x": 1.0, "y": 2.0, "z": 0.0},
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            }
        },
        "twist": {
            "twist": {
                "linear": {"x": 0.1, "y": 0.0, "z": 0.0},
                "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
            }
        },
    }


@pytest.fixture
def sample_battery_dict() -> dict[str, Any]:
    return {
        "voltage": 24.0,
        "current": -2.5,
        "percentage": 0.75,
        "present": True,
    }


@pytest.fixture
def sample_image_bytes() -> bytes:
    """1x1 RGB изображение (3 байта)."""
    try:
        import numpy as np
        return np.zeros((8, 8, 3), dtype=np.uint8).tobytes()
    except ImportError:
        return b"\x00" * (8 * 8 * 3)


# ─── Mock SmolVLA ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_smolvla_inference():
    """Мок SmolVLAInference, возвращающий фиксированные actions."""
    mock = AsyncMock()
    try:
        import numpy as np
        mock.infer.return_value = (np.zeros((50, 7)), 15.0)
    except ImportError:
        mock.infer.return_value = ([[0.0] * 7] * 50, 15.0)
    return mock


# ─── Mock rclpy Node ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_ros_node():
    """Мок rclpy.Node для тестов без ROS 2."""
    node = MagicMock()
    node.get_logger.return_value = MagicMock()
    node.create_publisher.return_value = MagicMock()
    node.create_subscription.return_value = MagicMock()
    node.create_timer.return_value = MagicMock()
    node.get_clock.return_value = MagicMock()
    return node
