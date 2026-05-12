"""Web search and URL parsing service using DuckDuckGo and httpx."""

import base64
import logging
import re
from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.9",
}


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_external_result_url(url: str) -> bool:
    candidate = str(url or "").strip().lower()
    if not candidate.startswith(("http://", "https://")):
        return False
    blocked = (
        "duckduckgo.com",
        "duck.com",
        "bing.com",
        "bing.com/ck/a",
        "search.brave.com/search",
        "imgs.search.brave.com",
        "yandex.ru/search",
        "yandex.com/search",
        "yandex.ru/clck",
        "yandex.com/clck",
    )
    return not any(host in candidate for host in blocked)


def _normalize_result_url(raw_url: str) -> str:
    url = unescape(str(raw_url or "")).strip()

    # DuckDuckGo redirect format
    if "uddg=" in url:
        actual = re.search(r"uddg=([^&]+)", url)
        url = unquote(actual.group(1)) if actual else url

    # Protocol-relative URL
    if url.startswith("//"):
        url = "https:" + url

    # Bing redirect format: /ck/a?...&u=a1<base64url>
    if url.startswith("/"):
        url = f"https://www.bing.com{url}"
    if "bing.com/ck/a" in url:
        try:
            parsed = urlparse(url)
            u_val = (parse_qs(parsed.query).get("u") or [""])[0]
            if u_val.startswith("a1"):
                u_val = u_val[2:]
            if u_val:
                padding = "=" * ((4 - (len(u_val) % 4)) % 4)
                decoded = base64.urlsafe_b64decode((u_val + padding).encode("utf-8")).decode(
                    "utf-8", "ignore"
                )
                if decoded.startswith(("http://", "https://")):
                    url = decoded
        except Exception:
            logger.debug("Failed to decode Bing redirect URL", exc_info=True)

    # Yandex redirect/search formats
    try:
        parsed = urlparse(url)
        if parsed.netloc.endswith(("yandex.ru", "yandex.com")):
            qs = parse_qs(parsed.query)
            if qs.get("url"):
                target = unquote((qs.get("url") or [""])[0])
                if target.startswith(("http://", "https://")):
                    url = target
    except Exception:
        logger.debug("Failed to normalize Yandex URL", exc_info=True)

    return url


async def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo HTML and return results.

    Returns list of {title, url, snippet}.
    """
    results: list[dict] = []

    def _append_unique(url: str, title: str, snippet: str) -> None:
        normalized = _normalize_result_url(url)
        if not _is_external_result_url(normalized):
            return
        normalized = normalized.strip()
        if any((r.get("url") or "") == normalized for r in results):
            return
        results.append(
            {
                "title": (title or "").strip(),
                "url": normalized,
                "snippet": (snippet or "").strip(),
            }
        )

    def _parse_duckduckgo_html(html: str) -> None:
        # Prefer canonical DuckDuckGo anchors and read nearby snippet text.
        anchors = list(
            re.finditer(
                r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                re.S | re.I,
            )
        )

        if not anchors:
            anchors = list(
                re.finditer(
                    r'<a[^>]+href="(https?://[^"]+|[^"]*uddg=[^"]+)"[^>]*>(.*?)</a>',
                    html,
                    re.S | re.I,
                )
            )

        for match in anchors:
            if len(results) >= num_results:
                break

            raw_url = (match.group(1) or "").strip()

            title = _strip_html(match.group(2) or "")
            tail = html[match.end() : match.end() + 1200]
            snippet_match = re.search(
                r'<(?:a|div|span|p)[^>]+class="[^"]*(?:result__snippet|snippet)[^"]*"[^>]*>(.*?)</(?:a|div|span|p)>',
                tail,
                re.S | re.I,
            )
            snippet = _strip_html(snippet_match.group(1)) if snippet_match else ""
            _append_unique(raw_url, title, snippet)

    def _parse_bing_html(html: str) -> None:
        blocks = re.findall(r'<li[^>]+class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>', html, re.S | re.I)
        for block in blocks:
            if len(results) >= num_results:
                break
            link_match = re.search(
                r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S | re.I
            )
            if not link_match:
                continue
            raw_url = (link_match.group(1) or "").strip()
            title = _strip_html(link_match.group(2) or "")
            snippet_match = re.search(
                r'<div[^>]+class="[^"]*b_caption[^"]*"[^>]*>.*?<p[^>]*>(.*?)</p>',
                block,
                re.S | re.I,
            )
            snippet = _strip_html(snippet_match.group(1)) if snippet_match else ""
            _append_unique(raw_url, title, snippet)

    def _parse_yandex_html(html: str) -> None:
        lowered = html.lower()
        if "верификац" in lowered or "captcha" in lowered:
            logger.info("Yandex returned verification page, skipping parser")
            return

        # Yandex SERP often keeps links inside h2.organic__title-wrapper a or plain h2 > a.
        blocks = re.findall(
            r'<li[^>]+class="[^"]*(?:serp-item|organic)[^"]*"[^>]*>(.*?)</li>', html, re.S | re.I
        )
        for block in blocks:
            if len(results) >= num_results:
                break
            link_match = re.search(
                r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                block,
                re.S | re.I,
            )
            if not link_match:
                link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S | re.I)
            if not link_match:
                continue

            raw_url = (link_match.group(1) or "").strip()
            title = _strip_html(link_match.group(2) or "")

            snippet_match = re.search(
                r'<div[^>]+class="[^"]*(?:organic__text|text-container|ExtendedText)[^"]*"[^>]*>(.*?)</div>',
                block,
                re.S | re.I,
            )
            snippet = _strip_html(snippet_match.group(1)) if snippet_match else ""
            _append_unique(raw_url, title, snippet)

    def _parse_brave_html(html: str) -> None:
        web_positions = [m.start() for m in re.finditer(r'data-type="web"', html, re.I)]
        for idx, pos in enumerate(web_positions):
            if len(results) >= num_results:
                break

            end = (
                web_positions[idx + 1]
                if idx + 1 < len(web_positions)
                else min(len(html), pos + 8000)
            )
            block = html[pos:end]

            link_match = re.search(r'<a[^>]+href="(https?://[^"]+)"[^>]*>', block, re.S | re.I)
            if not link_match:
                continue

            raw_url = (link_match.group(1) or "").strip()

            title_match = re.search(
                r'<div[^>]+class="[^"]*(?:search-snippet-title|title)[^"]*"[^>]*>(.*?)</div>',
                block,
                re.S | re.I,
            )
            if title_match:
                title = _strip_html(title_match.group(1) or "")
            else:
                anchor_text_match = re.search(
                    r'<a[^>]+href="https?://[^"]+"[^>]*>(.*?)</a>',
                    block,
                    re.S | re.I,
                )
                title = _strip_html(anchor_text_match.group(1) if anchor_text_match else "")

            snippet_match = re.search(
                r'<div[^>]+class="[^"]*generic-snippet[^"]*"[^>]*>.*?<div[^>]+class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                block,
                re.S | re.I,
            )
            snippet = _strip_html(snippet_match.group(1)) if snippet_match else ""
            _append_unique(raw_url, title, snippet)

        # Fallback: if structured blocks changed, still pick external anchors from page
        if not results:
            for href, text in re.findall(
                r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I
            ):
                if len(results) >= num_results:
                    break
                raw_url = (href or "").strip()
                title = _strip_html(text or "")
                if len(title) < 12:
                    continue
                _append_unique(raw_url, title, "")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for base in ("https://html.duckduckgo.com/html/?q=", "https://duckduckgo.com/html/?q="):
                url = f"{base}{quote_plus(query)}"
                resp = await client.get(url, headers=_HEADERS)
                resp.raise_for_status()
                html = resp.text

                _parse_duckduckgo_html(html)
                if results:
                    break

        # Если всё равно пусто — логируем html для отладки
        if not results:
            logger.warning("DuckDuckGo: не найдено результатов, html обрезан: %s", html[:2000])

    except Exception:
        logger.exception("Web search failed for query: %s", query)

    if not results:
        try:
            url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers=_HEADERS)
                html = resp.text

            links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I)
            for link_url, link_title in links:
                if len(results) >= num_results:
                    break
                link_url = (link_url or "").strip()
                _append_unique(link_url, _strip_html(link_title), "")
        except Exception:
            logger.debug("Lite search fallback also failed")

    if not results:
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers=_HEADERS)
                resp.raise_for_status()
                html = resp.text
            _parse_bing_html(html)
        except Exception:
            logger.debug("Bing fallback also failed")

    if not results:
        try:
            url = f"https://search.brave.com/search?q={quote_plus(query)}"
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers=_HEADERS)
                resp.raise_for_status()
                html = resp.text
            _parse_brave_html(html)
        except Exception:
            logger.debug("Brave fallback also failed")

    if not results:
        try:
            url = f"https://yandex.ru/search/?text={quote_plus(query)}"
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers=_HEADERS)
                resp.raise_for_status()
                html = resp.text
            _parse_yandex_html(html)
        except Exception:
            logger.debug("Yandex fallback also failed")

    return results


async def parse_url(url: str, max_chars: int = 5000) -> dict:
    """Fetch and extract text content from a URL.

    Returns {url, title, content, error}.
    """
    normalized_url = str(url or "").strip()
    if normalized_url and not re.match(r"^https?://", normalized_url, re.I):
        normalized_url = f"https://{normalized_url}"

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(normalized_url, headers=_HEADERS)
            resp.raise_for_status()
            html = resp.text

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        title = _strip_html(title_match.group(1)) if title_match else ""

        content = ""
        for selector in [
            r"<article[^>]*>(.*?)</article>",
            r"<main[^>]*>(.*?)</main>",
            r'class="content"[^>]*>(.*?)</div>',
            r'class="post-content"[^>]*>(.*?)</div>',
            r"<body[^>]*>(.*?)</body>",
        ]:
            match = re.search(selector, html, re.S | re.I)
            if match:
                content = _strip_html(match.group(1))
                if len(content) > 100:
                    break

        # Fallback: извлекаем текст из параграфов, если «большие» блоки не помогли.
        if not content or len(content) < 100:
            paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.S | re.I)
            if paragraphs:
                joined = "\n".join(_strip_html(p) for p in paragraphs)
                joined = re.sub(r"\s+", " ", joined).strip()
                if len(joined) > len(content):
                    content = joined

        # Fallback для тяжёлых JS-страниц/anti-bot: берём description из head.
        if not content:
            desc_match = re.search(
                r'<meta[^>]+(?:name="description"|property="og:description")[^>]+content="([^"]+)"',
                html,
                re.I,
            )
            if desc_match:
                content = _strip_html(desc_match.group(1))

        if not content:
            content = _strip_html(html)

        if len(content) > max_chars:
            content = content[:max_chars] + "..."

        return {"url": normalized_url, "title": title, "content": content, "error": None}

    except Exception as exc:
        logger.exception("Failed to parse URL: %s", normalized_url)
        return {"url": normalized_url, "title": "", "content": "", "error": str(exc)}


async def web_search_and_summarize(query: str, num_results: int = 3) -> str:
    """Search web and return formatted results with snippets."""
    results = await web_search(query, num_results=num_results)
    if not results:
        return f"По запросу «{query}» результатов не найдено."

    lines = [f"**Результаты веб-поиска по запросу «{query}»:**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **[{r['title']}]({r['url']})**")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
        lines.append("")

    return "\n".join(lines)
