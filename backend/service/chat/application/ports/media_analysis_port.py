from __future__ import annotations

from abc import ABC, abstractmethod


class MediaAnalysisPort(ABC):
    @abstractmethod
    async def analyze_image(self, content_bytes: bytes, content_type: str, filename: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def transcribe_audio(self, content_bytes: bytes, filename: str) -> str:
        raise NotImplementedError
