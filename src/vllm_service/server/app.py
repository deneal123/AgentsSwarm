"""FastAPI application for OpenAI-compatible API server."""

import inspect
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from vllm import SamplingParams

# Checked once at import time; guards against API drift across vllm versions.
_SAMPLING_PARAMS_FIELDS: frozenset[str] = frozenset(
    inspect.signature(SamplingParams.__init__).parameters
)

from vllm_service.config import settings
from vllm_service.engine.vllm_engine import get_engine, initialize_engine, shutdown_engine
from vllm_service.models.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    CompletionChoice,
    CompletionRequest,
    CompletionResponse,
    ModelInfo,
    ModelList,
    Usage,
)

logger = logging.getLogger(__name__)

api_router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting vLLM service...")
    await initialize_engine()
    logger.info("vLLM service started successfully")
    yield
    logger.info("Shutting down vLLM service...")
    await shutdown_engine()
    logger.info("vLLM service stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="vLLM Service",
        description="OpenAI-compatible API server with Data Parallel support",
        version=settings.get("version", "0.0.0"),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_model_name() -> str:
    return os.environ.get(
        "VLLM_MODEL_NAME",
        settings.get("MODEL.model_name", "Qwen/Qwen2.5-7B-Instruct"),
    )


def _check_api_key(request: Request) -> None:
    api_key = os.environ.get("VLLM_API_KEY", "")
    if not api_key:
        return
    auth = request.headers.get("Authorization", "")
    provided = auth[7:] if auth.startswith("Bearer ") else request.headers.get("X-API-Key", "")
    if provided != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _create_sampling_params(
    request: ChatCompletionRequest | CompletionRequest,
) -> SamplingParams:
    stop = request.stop
    if isinstance(stop, str):
        stop = [stop]
    if not stop:
        stop = ["\nuser:", "\nassistant:"]

    candidates: dict[str, Any] = {
        "n": request.n or 1,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "top_k": request.top_k if request.top_k and request.top_k > 0 else -1,
        "min_p": request.min_p,
        "repetition_penalty": request.repetition_penalty,
        "stop": stop,
        "max_tokens": (
            request.max_tokens
            or getattr(request, "max_completion_tokens", None)
            or 512
        ),
        "presence_penalty": request.presence_penalty,
        "frequency_penalty": request.frequency_penalty,
        "logprobs": request.logprobs,
        "min_tokens": getattr(request, "min_tokens", 0),
        "logit_bias": getattr(request, "logit_bias", None),
        "ignore_eos": getattr(request, "ignore_eos", False),
        "stop_token_ids": getattr(request, "stop_token_ids", None),
        "skip_special_tokens": getattr(request, "skip_special_tokens", True),
        "spaces_between_special_tokens": getattr(request, "spaces_between_special_tokens", True),
        "truncate_prompt_tokens": getattr(request, "truncate_prompt_tokens", None),
        "prompt_logprobs": getattr(request, "prompt_logprobs", None),
    }
    kwargs = {k: v for k, v in candidates.items() if k in _SAMPLING_PARAMS_FIELDS}
    return SamplingParams(**kwargs)


def _usage(output) -> Usage:
    prompt_tokens = len(output.prompt_token_ids)
    completion_tokens = sum(len(o.token_ids) for o in output.outputs)
    return Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@api_router.get("/v1/models", response_model=ModelList)
async def list_models(request: Request) -> ModelList:
    _check_api_key(request)
    return ModelList(data=[ModelInfo(id=_get_model_name())])


@api_router.get("/v1/models/{model_id:path}", response_model=ModelInfo)
async def get_model(model_id: str, request: Request) -> ModelInfo:
    _check_api_key(request)
    name = _get_model_name()
    if model_id != name:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelInfo(id=name)


# ---------------------------------------------------------------------------
# Chat completions
# ---------------------------------------------------------------------------

@api_router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    chat_request: ChatCompletionRequest,
    raw_request: Request,
) -> ChatCompletionResponse | StreamingResponse:
    _check_api_key(raw_request)
    engine = get_engine()
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    messages = [{"role": m.role, "content": m.content} for m in chat_request.messages]
    sampling_params = _create_sampling_params(chat_request)

    try:
        if chat_request.stream:
            return StreamingResponse(
                _stream_chat(engine, messages, sampling_params, request_id, chat_request.model),
                media_type="text/event-stream",
            )
        output = await engine.chat(
            messages=messages,
            sampling_params=sampling_params,
            request_id=request_id,
        )
        return _build_chat_response(output, request_id, chat_request.model)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Chat completion failed for request %s", request_id)
        raise HTTPException(status_code=500, detail="Internal server error")


async def _stream_chat(engine, messages, sampling_params, request_id, model):
    created = int(time.time())
    prev_texts: dict[int, str] = {}
    async for output in engine.chat_stream(
        messages=messages,
        sampling_params=sampling_params,
        request_id=request_id,
    ):
        for item in output.outputs:
            prev = prev_texts.get(item.index, "")
            delta = item.text[len(prev):]
            prev_texts[item.index] = item.text
            chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": item.index,
                    "delta": {"content": delta},
                    "finish_reason": item.finish_reason,
                }],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def _build_chat_response(output, request_id: str, model: str) -> ChatCompletionResponse:
    choices = [
        ChatCompletionChoice(
            index=item.index,
            message=ChatMessage(role="assistant", content=item.text),
            finish_reason=item.finish_reason,
        )
        for item in output.outputs
    ]
    return ChatCompletionResponse(
        id=request_id,
        created=int(time.time()),
        model=model,
        choices=choices,
        usage=_usage(output),
    )


# ---------------------------------------------------------------------------
# Text completions
# ---------------------------------------------------------------------------

@api_router.post("/v1/completions", response_model=None)
async def completions(
    completion_request: CompletionRequest,
    raw_request: Request,
) -> CompletionResponse | StreamingResponse:
    _check_api_key(raw_request)
    engine = get_engine()
    request_id = f"cmpl-{uuid.uuid4().hex[:8]}"

    prompt = completion_request.prompt
    if isinstance(prompt, list):
        prompt = prompt[0] if prompt else ""

    sampling_params = _create_sampling_params(completion_request)

    try:
        if completion_request.stream:
            return StreamingResponse(
                _stream_completion(engine, prompt, sampling_params, request_id, completion_request.model),
                media_type="text/event-stream",
            )
        output = await engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        )
        return _build_completion_response(output, request_id, completion_request.model)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Completion failed for request %s", request_id)
        raise HTTPException(status_code=500, detail="Internal server error")


async def _stream_completion(engine, prompt, sampling_params, request_id, model):
    created = int(time.time())
    prev_texts: dict[int, str] = {}
    # generate_stream is an async generator — do NOT await it
    async for output in engine.generate_stream(
        prompt=prompt,
        sampling_params=sampling_params,
        request_id=request_id,
    ):
        for item in output.outputs:
            prev = prev_texts.get(item.index, "")
            delta = item.text[len(prev):]
            prev_texts[item.index] = item.text
            chunk = {
                "id": request_id,
                "object": "text_completion",
                "created": created,
                "model": model,
                "choices": [{
                    "index": item.index,
                    "text": delta,
                    "finish_reason": item.finish_reason,
                }],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def _build_completion_response(output, request_id: str, model: str) -> CompletionResponse:
    choices = [
        CompletionChoice(
            index=item.index,
            text=item.text,
            finish_reason=item.finish_reason,
        )
        for item in output.outputs
    ]
    return CompletionResponse(
        id=request_id,
        created=int(time.time()),
        model=model,
        choices=choices,
        usage=_usage(output),
    )


# ---------------------------------------------------------------------------
# Tokenize / Detokenize
# ---------------------------------------------------------------------------

@api_router.post("/tokenize")
async def tokenize(request: Request) -> dict[str, Any]:
    _check_api_key(request)
    body = await request.json()
    token_ids = await get_engine().tokenize(body.get("text", ""))
    return {"token_ids": token_ids, "count": len(token_ids)}


@api_router.post("/detokenize")
async def detokenize(request: Request) -> dict[str, Any]:
    _check_api_key(request)
    body = await request.json()
    text = await get_engine().detokenize(body.get("token_ids", []))
    return {"text": text}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@api_router.get("/health")
async def health_check() -> dict[str, str]:
    healthy = await get_engine().is_healthy()
    return {"status": "healthy" if healthy else "unhealthy"}


@api_router.get("/ready")
async def readiness_check() -> dict[str, str]:
    ready = await get_engine().is_healthy()
    return {"status": "ready" if ready else "not ready"}
