"""Deep Research tool: multi-step web research with synthesis."""

import asyncio
import logging
<<<<<<< HEAD
from collections.abc import Callable
from typing import AsyncGenerator, Optional
=======
from collections.abc import AsyncGenerator
>>>>>>> 768598397002f0ab034484bd966612234d78ea3c

from service.services.agents.domain.client import create_chat_completion
from service.services.agents.domain.tools.web_search import parse_url, web_search

logger = logging.getLogger(__name__)

_RESEARCH_PLAN_PROMPT = """Ты — ведущий исследователь и планировщик.
Пользователь дал тему для глубокого исследования: {topic}

Сгенерируй 4-6 поисковых запросов, которые покрывают тему системно:
- базовые факты и контекст,
- текущие тренды/данные,
- критика, риски, ограничения,
- практические кейсы или примеры внедрения.

Требования:
- запросы должны быть конкретными и разнообразными,
- избегай дубликатов и слишком общих формулировок,
- формулируй так, чтобы получить содержательные источники.

Верни ТОЛЬКО JSON-массив строк, без markdown и комментариев.
Пример: ["...", "...", "..."]"""

_SYNTHESIS_PROMPT = """Ты — ведущий аналитик и автор исследовательских отчётов.

Подготовь глубокий, но практичный отчёт по теме: {topic}
Используй собранные данные ниже как основу фактов.

Требования к качеству:
1) Ответ в Markdown с чёткой структурой:
    - TL;DR (3-6 ключевых выводов)
    - Контекст
    - Основные наблюдения и факты
    - Сравнение подходов / точек зрения
    - Риски и ограничения
    - Практические рекомендации
    - Итог
2) Если данных недостаточно или они противоречат друг другу — явно обозначь это.
3) Не выдумывай источники и числа.
4) Сохраняй аналитический стиль, без воды.

Собранные данные:
{data}"""


async def deep_research(
    topic: str,
    model: str,
<<<<<<< HEAD
    on_status: Optional[Callable] = None,
) -> AsyncGenerator[str, None]:
=======
    on_status: callable | None = None,
) -> AsyncGenerator[str]:
>>>>>>> 768598397002f0ab034484bd966612234d78ea3c
    """Perform multi-step deep research on a topic.

    Yields status updates and the final report as markdown chunks.
    """
    import json

    yield "**Этап 1/4:** Составляю план исследования...\n\n"

    try:
        plan_resp = await create_chat_completion(
            messages=[
                {"role": "system", "content": "Ты помощник. Отвечай ТОЛЬКО JSON."},
                {"role": "user", "content": _RESEARCH_PLAN_PROMPT.format(topic=topic)},
            ],
            model=model,
            temperature=0.3,
            max_tokens=500,
        )
        plan_text = getattr(plan_resp.choices[0].message, "content", "") or "[]"
        plan_text = plan_text.strip()
        if plan_text.startswith("```"):
            plan_text = plan_text.split("\n", 1)[-1]
        if plan_text.endswith("```"):
            plan_text = plan_text.rsplit("```", 1)[0]

        queries = json.loads(plan_text.strip())
        if not isinstance(queries, list):
            queries = [topic]
        queries = [str(q).strip() for q in queries if str(q).strip()]
        if not queries:
            queries = [topic, f"{topic} обзор", f"{topic} анализ"]
    except Exception:
        logger.warning("Failed to parse research plan, using topic-derived queries")
        queries = [
            topic,
            f"{topic} обзор",
            f"{topic} анализ",
            f"{topic} критика",
            f"{topic} примеры",
        ]

    queries = queries[:4]

    yield f"**План исследования:** {len(queries)} направлений поиска\n"
    for i, q in enumerate(queries, 1):
        yield f"  {i}. {q}\n"
    yield "\n"

    yield "**Этап 2/4:** Выполняю веб-поиск...\n\n"

    all_results = []
    for i, query in enumerate(queries):
        yield f"🔍 Поиск {i + 1}/{len(queries)}: «{query}»\n"
        try:
            results = await asyncio.wait_for(web_search(query, num_results=4), timeout=16)
        except TimeoutError:
            logger.warning("web_search timeout for %r", query)
            results = []
        except Exception as exc:
            logger.warning("web_search failed for %r: %s", query, exc)
            results = []
        all_results.extend(results)
        yield f"   → Найдено {len(results)} результатов\n"

    yield f"\n**Всего найдено:** {len(all_results)} источников\n\n"

    yield "**Этап 3/4:** Анализирую источники...\n\n"

    collected_data = []
    urls_seen = set()
    parse_failures = 0
    for r in all_results[:8]:
        url = r.get("url", "")
        if url in urls_seen or not url:
            continue
        urls_seen.add(url)

        yield f"📄 Читаю: {r.get('title', url)[:60]}...\n"
        try:
            parsed = await asyncio.wait_for(parse_url(url, max_chars=2200), timeout=8)
        except TimeoutError:
            logger.info("parse_url timeout for %s", url)
            parsed = {}
            parse_failures += 1
        except Exception as exc:
            logger.info("parse_url failed for %s: %s", url, exc)
            parsed = {}
            parse_failures += 1

        parsed_content = str(parsed.get("content") or "").strip()
        snippet = str(r.get("snippet") or "").strip()

        if parsed_content and len(parsed_content) > 20:
            content = parsed_content[:2000]
        elif snippet:
            content = snippet
        else:
            parse_failures += 1
            continue

        collected_data.append(
            {
                "title": parsed.get("title") or r.get("title", "") or url,
                "url": url,
                "content": content,
                "snippet": snippet,
            }
        )

    yield f"\n**Проанализировано:** {len(collected_data)} источников"
    if parse_failures:
        yield f" (пропущено {parse_failures} из-за недоступности контента)"
    yield "\n\n"

    if not collected_data:
        yield "**Этап 4/4:** Синтезирую отчёт...\n\n---\n\n"
        yield (
            "⚠️ Внешние источники по теме сейчас недоступны (поиск вернул 0 результатов или страницы не читаются).\n\n"
            "### Что можно сделать дальше\n"
            "1. Уточнить запрос (добавить язык, страну, период).\n"
            "2. Повторить позже (часто это временные anti-bot/timeout ограничения).\n"
            "3. Дать 2-5 конкретных ссылок — я сразу выполню их глубокий разбор.\n"
        )
        yield "\n\n---\n\n### Источники\n"
        return

    yield "**Этап 4/4:** Синтезирую отчёт...\n\n---\n\n"

    def _build_data_text(limit_chars_per_source: int) -> str:
        chunks: list[str] = []
        for i, d in enumerate(collected_data, 1):
            chunks.append(
                f"\n### Источник {i}: {d['title']}\nURL: {d['url']}\n"
                f"{d['content'][:limit_chars_per_source]}\n"
            )
        return "".join(chunks)

    data_text = _build_data_text(1500)
    if not data_text:
        data_text = "Данные из веб-поиска не получены. Сформируй отчёт на основе надёжных общих знаний, но явно отметь, что внешние источники недоступны."

    last_error: Exception | None = None
    report = ""
    for attempt_limit in (14000, 9000, 5000):
        trimmed = data_text[:attempt_limit]
        try:
            synthesis_resp = await create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": _SYNTHESIS_PROMPT.format(topic=topic, data=trimmed),
                    },
                    {
                        "role": "user",
                        "content": f"Составь подробный аналитический отчёт по теме: {topic}",
                    },
                ],
                model=model,
                temperature=0.4,
                max_tokens=3000,
            )
            report = getattr(synthesis_resp.choices[0].message, "content", "") or ""
            if report.strip():
                last_error = None
                break
        except Exception as exc:
            last_error = exc
            logger.warning("synthesis attempt failed at limit=%d: %s", attempt_limit, exc)
            continue

    if report.strip():
        yield report
    else:
        logger.exception("Failed to synthesize research report", exc_info=last_error)
        err_detail = f" ({last_error})" if last_error else ""
        yield f"⚠️ Не удалось сгенерировать отчёт{err_detail}. Ниже — собранные источники и краткие выжимки:\n\n"
        for d in collected_data:
            yield f"- **[{d['title']}]({d['url']})** — {(d.get('snippet') or d.get('content', ''))[:240]}\n"

    yield "\n\n---\n\n### Источники\n"
    for i, d in enumerate(collected_data, 1):
        yield f"{i}. [{d['title']}]({d['url']})\n"
