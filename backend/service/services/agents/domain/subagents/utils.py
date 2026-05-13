"""Helpers for sub-agent model selection."""

import re


def pick_text_model(models: list[str]) -> str | None:
    text_re = re.compile(r"(gpt|qwen|llama|mistral|alpha|instruct|chat)", re.I)
    return next((m for m in models if text_re.search(m)), models[0] if models else None)


def pick_image_model(models: list[str]) -> str | None:
    image_re = re.compile(r"(image|dall|stable|flux|kandinsky|sdxl)", re.I)
    return next((m for m in models if image_re.search(m)), None)
