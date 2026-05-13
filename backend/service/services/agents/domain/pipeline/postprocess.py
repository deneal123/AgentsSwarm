"""Post-processing hooks for agent pipeline."""

from __future__ import annotations

from .context_enricher import schedule_memory_extraction


def run_post_response_hooks(
    *,
    user_id: int | str | None,
    thread_id: str,
    user_input: str,
    logger,
) -> None:
    """Execute non-blocking post-response hooks.

    Current hooks:
    - background memory extraction
    """
    if not user_id:
        return

    try:
        schedule_memory_extraction(str(user_id), thread_id, user_input, logger)
    except Exception:
        logger.debug("Post-response hooks failed", exc_info=True)
