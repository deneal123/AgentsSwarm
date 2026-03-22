from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class BaseRobotSpawner(ABC):
    """Абстрактный спавнер роботов."""

    def __init__(self, world) -> None:
        self.world = world

    @abstractmethod
    def spawn_robots(self, count: int, positions: Sequence | None = None):
        raise NotImplementedError
