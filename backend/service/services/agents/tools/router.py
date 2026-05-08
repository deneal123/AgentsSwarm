from __future__ import annotations

import json
import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

InputType = Literal["text", "image", "audio", "video"]

_TEXT_FAMILY_RE = re.compile(r"(gpt|qwen|llama|mistral|gemma|deepseek|yi|phi|glm|kimi|instruct|chat|alpha)", re.I)
_CODE_FAMILY_RE = re.compile(r"(kodify|code|coder|codestral|starcoder|deepseek.*coder|qwen.*coder)", re.I)
_IMAGE_FAMILY_RE = re.compile(r"(image|vision|vl|multimodal|dall-e|sdxl|flux)", re.I)
_AUDIO_FAMILY_RE = re.compile(r"(whisper|audio|speech|asr|stt)", re.I)
_VIDEO_FAMILY_RE = re.compile(r"(video|vision|vl|multimodal)", re.I)
_LARGE_MODEL_RE = re.compile(r"(357b|235b|120b|70b|72b|480b|pro|alpha)", re.I)
_SMALL_MODEL_RE = re.compile(r"(8b|20b|lightning|mini|small)", re.I)
_FAST_MODEL_RE = re.compile(r"(8b|7b|4b|3b|mini|small|lite|flash|lightning|fast)", re.I)


def _is_chat_capable_model(model_id: str | None) -> bool:
    low = str(model_id or "").strip().lower()
    if not low:
        return False
    blocked_markers = (
        "bge", "e5", "gte", "embed", "embedding", "rerank", "ranker",
        "whisper", "asr", "stt", "tts", "speech-to-text", "text-to-speech",
    )
    return not any(marker in low for marker in blocked_markers)

_ROUTER_SYSTEM = """\
Ты — высокоточный роутер GPTHub.
Вход: сообщение пользователя, модальности и список доступных ID моделей.
Цель: выбрать лучшую модель и один инструментальный маршрут с минимальным числом ошибок.

Верни РОВНО один JSON-объект, без markdown и комментариев:
{"model":"<точный id из переданного списка>","tool":"none|general|web_search|deep_research|audio_transcribe|image_gen|pptx_gen","reason":"<до 12 слов>"}

Жёсткие ограничения:
1) "model" должен точно совпадать с одним из переданных ID (регистр можно игнорировать).
2) "tool" должен быть только из разрешённых значений выше.
3) "reason" должен быть коротким и конкретным.
4) Если есть сомнения, выбирай консервативный маршрут: tool="none" или "general".

Политика выбора инструмента:
- image_gen: явный запрос сгенерировать/нарисовать/создать изображение, иллюстрацию, арт.
- pptx_gen: явный запрос на слайды/презентацию/deck/.pptx.
- deep_research: глубокий многоисточниковый анализ, отчёт, сравнение подходов, длинное исследование.
- web_search: нужны актуальные/живые факты (новости, цены, релизы, погода, "сегодня", "сейчас").
- audio_transcribe: пользователь прислал аудио/голос и просит распознать речь (STT, транскрипт).
- general: специализированный запрос без отдельного инструмента, но с обычным рассуждением ассистента.
- none: по умолчанию, когда отдельный инструментальный маршрут не требуется.

Политика выбора модели:
- Для image-ввода: предпочитай vision/мультимодальные модели.
- Для audio-ввода: предпочитай ASR/аудио-совместимые модели.
- Для задач с кодом: предпочитай coder/code модели.
- Для сложного анализа: предпочитай более мощные/крупные модели.
- Для коротких и простых задач: предпочитай быстрые/лёгкие модели.
- Фолбэк: наиболее сильная универсальная текстовая модель.
"""

_ROUTER_USER_TMPL = """\
Модальности: {modalities}
Модели: {models}

Сообщение: {message}"""


def _normalize_models(models: list[str] | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in models or []:
        model_id = str(item or "").strip()
        if not model_id:
            continue
        if not _is_chat_capable_model(model_id):
            continue
        key = model_id.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(model_id)
    return ordered


def _pick_first(models: list[str], pattern: re.Pattern[str]) -> str | None:
    for model in models:
        if pattern.search(model):
            return model
    return None


def _pick_router_model(models: list[str]) -> str | None:
    fast = _pick_first(models, _FAST_MODEL_RE)
    if fast:
        return fast
    text = _pick_first(models, _TEXT_FAMILY_RE)
    if text:
        return text
    return models[0] if models else None


_VALID_TOOLS = {"none", "web_search", "deep_research", "audio_transcribe", "image_gen", "pptx_gen", "general"}


def _parse_llm_response(raw: str, available_models: list[str]) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)

    model = data.get("model")
    if model and not any(m.lower() == model.lower() for m in available_models):
        model = None

    tool = data.get("tool", "none")
    if tool not in _VALID_TOOLS:
        tool = "none"

    return {
        "model": model,
        "tool": tool,
        "reason": str(data.get("reason", "")),
    }


async def _llm_route(
    text: str,
    models: list[str],
    router_model: str,
    input_type: str | None,
) -> dict | None:
    try:
        from service.services.agents.client import create_chat_completion

        modalities = input_type if input_type and input_type != "text" else "text"
        if input_type and input_type != "text":
            modalities = f"text + {input_type}"

        response = await create_chat_completion(
            messages=[
                {"role": "system", "content": _ROUTER_SYSTEM},
                {
                    "role": "user",
                    "content": _ROUTER_USER_TMPL.format(
                        modalities=modalities,
                        models=", ".join(models) if models else "unknown",
                        message=text[:2000],
                    ),
                },
            ],
            model=router_model,
            temperature=0.0,
            max_tokens=150,
        )
        raw = (response.choices[0].message.content or "").strip()
        return _parse_llm_response(raw, models)
    except Exception:
        logger.debug("LLM router failed, will use regex fallback", exc_info=True)
        return None


def _detect_input_type(text: str, input_type: str | None) -> InputType:
    if isinstance(input_type, str):
        normalized = input_type.strip().lower()
        if normalized in {"text", "image", "audio", "video"}:
            return normalized  # type: ignore[return-value]

    low = (text or "").lower()
    if re.search(r"\.(png|jpg|jpeg|webp|gif|svg)\b|\bimage\b|\bphoto\b|изображ", low):
        return "image"
    if re.search(r"\.(mp3|wav|m4a|ogg|flac)\b|\baudio\b|\bspeech\b|\bvoice\b|аудио", low):
        return "audio"
    if re.search(r"\.(mp4|mov|avi|mkv|webm)\b|\bvideo\b|видео", low):
        return "video"
    return "text"


def _detect_text_kind(text: str) -> Literal["general", "code"]:
    low = (text or "").lower()
    if re.search(r"```|\bdef\b|\bclass\b|\bimport\b|\bfunction\b|\bconst\b|\bvar\b|\btraceback\b|\bstack trace\b", low):
        return "code"
    return "general"


def _detect_text_complexity(text: str) -> Literal["low", "medium", "high"]:
    value = text or ""
    low = value.lower()
    score = 0
    if len(value) > 300:
        score += 1
    if len(value) > 1200:
        score += 1
    if value.count("\n") >= 4:
        score += 1
    complexity_terms = re.findall(
        r"\b(если|когда|треб|огранич|сложн|оптим|архитект|edge case|performance|optimi[sz]e|constraint|pipeline)\w*\b",
        low,
    )
    if len(complexity_terms) >= 2:
        score += 1
    if score >= 2:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def _regex_route(
    text: str,
    input_type: str | None,
    models: list[str],
) -> tuple[str | None, str, str | None, str | None, str]:
    routing_type = _detect_input_type(text, input_type)
    text_kind = None
    complexity = None
    resolved = None
    tool = "none"

    if routing_type == "image":
        resolved = _pick_first(models, _IMAGE_FAMILY_RE)
    elif routing_type == "audio":
        tool = "audio_transcribe"
        resolved = _pick_first(models, _TEXT_FAMILY_RE)
        routing_type = "text"
    elif routing_type == "video":
        resolved = _pick_first(models, _VIDEO_FAMILY_RE)

    if routing_type == "text":
        text_kind = _detect_text_kind(text)
        complexity = _detect_text_complexity(text)
        if text_kind == "code":
            resolved = _pick_first(models, _CODE_FAMILY_RE)
        if not resolved:
            if complexity == "high":
                resolved = _pick_first(models, _LARGE_MODEL_RE)
            elif complexity == "low":
                resolved = _pick_first(models, _SMALL_MODEL_RE)
        if not resolved:
            resolved = _pick_first(models, _TEXT_FAMILY_RE)

    if not resolved and models:
        resolved = models[0]

    return resolved, routing_type, text_kind, complexity, tool


async def route_model(
    *,
    text: str,
    selected_model: str | None,
    input_type: str | None,
    available_models: list[str] | None = None,
) -> tuple[str | None, dict]:
    """Resolve effective model and tool according to routing rules."""
    models = _normalize_models(available_models)
    if not models:
        try:
            from service.services.agents.client import list_available_models

            models = _normalize_models(await list_available_models())
        except Exception:
            models = []

    meta: dict = {
        "requested_model": selected_model,
        "available_models_count": len(models),
    }

    manual_model = (selected_model or "").strip()
    if manual_model and manual_model.lower() != "auto":
        if not _is_chat_capable_model(manual_model):
            meta["manual_model_blocked"] = manual_model
        elif not models or any(m.lower() == manual_model.lower() for m in models):
            return manual_model, {
                **meta,
                "input_type": _detect_input_type(text, input_type),
                "source": "manual",
            }
        else:
            meta["manual_model_missing"] = manual_model

    router_model = _pick_router_model(models)
    if router_model:
        llm_result = await _llm_route(text, models, router_model, input_type)
        if llm_result:
            resolved = llm_result["model"] or (models[0] if models else None)
            return resolved, {
                **meta,
                "input_type": input_type or "text",
                "tool": llm_result["tool"],
                "reason": llm_result["reason"],
                "router_model": router_model,
                "source": "llm",
            }

    resolved, routing_type, text_kind, complexity, tool = _regex_route(text, input_type, models)
    return resolved, {
        **meta,
        "input_type": routing_type,
        "tool": tool,
        "text_kind": text_kind,
        "complexity": complexity,
        "source": "regex_fallback",
    }
