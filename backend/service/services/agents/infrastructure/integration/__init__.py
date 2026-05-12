"""Agent integrations package.

Contains pluggable adapters for external services used by agent layer
(for example memory providers).
"""

from __future__ import annotations

from service.services.agents.infrastructure.integration.base import BaseIntegration, BaseMemoryIntegration, NoopMemoryIntegration
from service.services.agents.infrastructure.integration.memory import Mem0MemoryIntegration

_memory_integration_singleton: BaseMemoryIntegration | None = None


def get_memory_integration() -> BaseMemoryIntegration:
	"""Return singleton memory integration used by agent/services layer."""
	global _memory_integration_singleton
	if _memory_integration_singleton is None:
		integration = Mem0MemoryIntegration()
		_memory_integration_singleton = integration if integration.available else NoopMemoryIntegration()
	return _memory_integration_singleton


__all__ = [
	"BaseIntegration",
	"BaseMemoryIntegration",
	"NoopMemoryIntegration",
	"Mem0MemoryIntegration",
	"get_memory_integration",
]

