from __future__ import annotations

import base64
import io
import re

from service.services.agents.domain.client import get_openai_client, list_available_models
from service.services.chat.application.ports.media_analysis_port import MediaAnalysisPort


class OpenAIMediaAnalysisAdapter(MediaAnalysisPort):
    async def analyze_image(self, content_bytes: bytes, content_type: str, filename: str) -> str:
        client = get_openai_client()
        if client is None:
            return f"[Изображение загружено: {filename}]"

        image_data_url = (
            f"data:{content_type or 'image/png'};base64,{base64.b64encode(content_bytes).decode()}"
        )
        models = await list_available_models()
        vlm_re = re.compile(
            r"(vision|vl\b|vlm|multimodal|image|qwen.*vl|llava|gpt-4o|pixtral)", re.I
        )
        vlm_model = next((m for m in models if vlm_re.search(m)), None)
        if vlm_model is None:
            return f"[Изображение загружено: {filename}]"

        resp = await client.chat.completions.create(
            model=vlm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {
                            "type": "text",
                            "text": "Опиши подробно что изображено на этой картинке. Укажи все важные детали, объекты, текст, данные — всё что видишь.",
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )
        return (
            getattr(resp.choices[0].message, "content", "")
            or f"[Изображение загружено: {filename}]"
        )

    async def transcribe_audio(self, content_bytes: bytes, filename: str) -> str:
        client = get_openai_client()
        if client is None:
            return f"[Аудио файл: {filename}, транскрипция недоступна]"
        try:
            available = await list_available_models()
        except Exception:
            available = []
        available_lower = {m.lower(): m for m in available}
        preferred = ["whisper-medium", "whisper-turbo-local", "whisper-large-v3", "whisper-1"]
        candidates: list[str] = []
        for name in preferred:
            actual = available_lower.get(name.lower())
            if actual and actual not in candidates:
                candidates.append(actual)
        for m in available:
            low = m.lower()
            if ("whisper" in low or "asr" in low or "stt" in low) and m not in candidates:
                candidates.append(m)
        if not candidates:
            candidates = preferred[:2]

        for model_id in candidates:
            audio_file = io.BytesIO(content_bytes)
            audio_file.name = filename
            try:
                transcription = await client.audio.transcriptions.create(
                    model=model_id, file=audio_file
                )
                return transcription.text or "[Аудио не распознано]"
            except Exception:
                continue
        return f"[Аудио файл: {filename}, транскрипция недоступна]"
