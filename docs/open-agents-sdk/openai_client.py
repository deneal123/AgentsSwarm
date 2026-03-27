import os
import httpx
import logging
from openai import AsyncOpenAI
from agents import set_default_openai_key, set_default_openai_client, set_tracing_disabled

logger = logging.getLogger(__name__)


def _make_http_client():
    PROXY_HOST = os.getenv("PROXY_HOST")
    PROXY_PORT = os.getenv("PROXY_PORT")
    PROXY_USER = os.getenv("PROXY_USER")
    PROXY_PASS = os.getenv("PROXY_PASS")

    if PROXY_HOST and PROXY_PORT:
        try:
            proxy_url = f"http://{PROXY_USER or ''}:{PROXY_PASS or ''}@{PROXY_HOST}:{PROXY_PORT}"
            # httpx expects a mapping for proxies if auth is needed; simple string works too
            return httpx.AsyncClient(proxies=proxy_url)
        except Exception:
            logger.exception("Failed to build proxy client; falling back to default HTTP client")
    return httpx.AsyncClient()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

try:
    OPENAI_CLIENT = AsyncOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=BASE_URL,
        http_client=_make_http_client(),
    )
    set_default_openai_key(OPENAI_API_KEY)
    set_default_openai_client(OPENAI_CLIENT)
    set_tracing_disabled(disabled=True)
except Exception:
    logger.exception("Failed to initialize OpenAI client; OPENAI_CLIENT set to None")
    OPENAI_CLIENT = None
    # Do not set proxies env vars when not configured
    # os.environ["HTTP_PROXY"] = proxy_url
    # os.environ["HTTPS_PROXY"] = proxy_url