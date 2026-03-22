from abc import ABC, abstractmethod
from typing import Any


class BaseSceneBuilder(ABC):
	"""Базовый класс для создания и конфигурации сцены/мира."""

	@abstractmethod
	def build(self) -> Any:
		"""Вернуть сконфигурированный World (тип определяется isaacsim)."""
		raise NotImplementedError
