"""FastAPI application for OpenAI-compatible API server."""

import asyncio
import logging
import os
import time
import uuid
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from vllm import SamplingParams

from vllm_service.config import settings
from vllm_service.engine.vllm_engine import get_engine, initialize_engine, shutdown_engine
from vllm_service.models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    CompletionChoice,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingData,
    ErrorResponse,
    ErrorDetail,
    ModelInfo,
    ModelList,
    Usage,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting vLLM service...")
    await initialize_engine()
    logger.info("vLLM service started successfully")
    
    yield
    
    logger.info("Shutting down vLLM service...")
    await shutdown_engine()
    logger.info("vLLM service stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
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


from fastapi import APIRouter

api_router = APIRouter()


def _create_sampling_params(request: Union[ChatCompletionRequest, CompletionRequest]) -> SamplingParams:
    """Create SamplingParams from request."""
    # Normalize stop tokens for OpenAI-style conversation
    stop_tokens = None
    if request.stop:
        stop_tokens = request.stop if isinstance(request.stop, list) else [request.stop]
    else:
        # Prevent model from generating beyond one assistant response.
        stop_tokens = ["\nuser:", "\nassistant:"]
    
    params = SamplingParams(
        n=request.n or 1,
        temperature=request.temperature,
        top_p=request.top_p,
        top_k=request.top_k if request.top_k and request.top_k > 0 else -1,
        min_p=request.min_p,
        repetition_penalty=request.repetition_penalty,
        stop=stop_tokens,
        max_tokens=request.max_tokens or getattr(request, "max_completion_tokens", None) or 512,
        min_tokens=request.min_tokens if hasattr(request, 'min_tokens') else 0,
        presence_penalty=request.presence_penalty,
        frequency_penalty=request.frequency_penalty,
        logprobs=request.logprobs,
        logit_bias=request.logit_bias if hasattr(request, 'logit_bias') else None,
        ignore_eos=request.ignore_eos if hasattr(request, 'ignore_eos') else False,
        stop_token_ids=request.stop_token_ids if hasattr(request, 'stop_token_ids') else None,
        skip_special_tokens=request.skip_special_tokens if hasattr(request, 'skip_special_tokens') else True,
        spaces_between_special_tokens=request.spaces_between_special_tokens if hasattr(request, 'spaces_between_special_tokens') else True,
        truncate_prompt_tokens=request.truncate_prompt_tokens if hasattr(request, 'truncate_prompt_tokens') else None,
        prompt_logprobs=request.prompt_logprobs if hasattr(request, 'prompt_logprobs') else None,
    )
    return params


def _check_api_key(request: Request) -> None:
    """Validate API key if configured."""
    api_key = os.environ.get("VLLM_API_KEY", settings.get("default.server.api_key", ""))
    if api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            provided_key = auth_header[7:]
        else:
            provided_key = request.headers.get("X-API-Key", "")
        
        if provided_key != api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )


@api_router.get("/v1/models", response_model=ModelList)
async def list_models(request: Request) -> ModelList:
    """List available models."""
    _check_api_key(request)
    
    model_name = os.environ.get("VLLM_MODEL_NAME", settings.get("MODEL.model_name", settings.get("model_name", "Qwen/Qwen2.5-7B-Instruct")))
    model_info = ModelInfo(
        id=model_name,
        owned_by="vllm-service",
    )

    return ModelList(data=[model_info])


@api_router.get("/v1/models/{model_id:path}", response_model=ModelInfo)
async def get_model(model_id: str, request: Request) -> ModelInfo:
    """Get model information."""
    _check_api_key(request)
    
    model_name = os.environ.get("VLLM_MODEL_NAME", settings.get("MODEL.model_name", settings.get("model_name", "Qwen/Qwen2.5-7B-Instruct")))
    if model_id != model_name:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return ModelInfo(
        id=model_name,
        owned_by="vllm-service",
    )


@api_router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    chat_request: ChatCompletionRequest,
    raw_request: Request,
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """Create chat completion."""
    _check_api_key(raw_request)
    
    engine = get_engine()
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    
    messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]
    
    sampling_params = _create_sampling_params(chat_request)
    
    try:
        if chat_request.stream:
            return StreamingResponse(
                _stream_chat_response(
                    engine=engine,
                    messages=messages,
                    sampling_params=sampling_params,
                    request_id=request_id,
                    model=chat_request.model,
                ),
                media_type="text/event-stream",
            )
        else:
            output = await engine.chat(
                messages=messages,
                sampling_params=sampling_params,
                request_id=request_id,
            )
            
            return _build_chat_response(output, request_id, chat_request.model)
    
    except Exception as e:
        logger.exception("Chat completion failed")
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_chat_response(
    engine,
    messages: List[Dict],
    sampling_params: SamplingParams,
    request_id: str,
    model: str,
):
    """Stream chat completion response."""
    created = int(time.time())
    
    async for output in engine.chat_stream(
        messages=messages,
        sampling_params=sampling_params,
        request_id=request_id,
    ):
        for output_item in output.outputs:
            chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": output_item.index,
                    "delta": {"content": output_item.text},
                    "finish_reason": output_item.finish_reason,
                }]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    
    yield "data: [DONE]\n\n"


def _build_chat_response(output, request_id: str, model: str) -> ChatCompletionResponse:
    """Build chat completion response from engine output."""
    choices = []
    for output_item in output.outputs:
        choice = ChatCompletionChoice(
            index=output_item.index,
            message=ChatMessage(
                role="assistant",
                content=output_item.text,
            ),
            finish_reason=output_item.finish_reason,
        )
        choices.append(choice)
    
    usage = Usage(
        prompt_tokens=len(output.prompt_token_ids),
        completion_tokens=sum(len(o.token_ids) for o in output.outputs),
        total_tokens=len(output.prompt_token_ids) + sum(len(o.token_ids) for o in output.outputs),
    )
    
    return ChatCompletionResponse(
        id=request_id,
        created=int(time.time()),
        model=model,
        choices=choices,
        usage=usage,
    )


@api_router.post("/v1/completions", response_model=None)
async def completions(
    completion_request: CompletionRequest,
    raw_request: Request,
) -> Union[CompletionResponse, StreamingResponse]:
    """Create text completion."""
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
                _stream_completion_response(
                    engine=engine,
                    prompt=prompt,
                    sampling_params=sampling_params,
                    request_id=request_id,
                    model=completion_request.model,
                ),
                media_type="text/event-stream",
            )
        else:
            output = await engine.generate(
                prompt=prompt,
                sampling_params=sampling_params,
                request_id=request_id,
            )
            
            return _build_completion_response(output, request_id, completion_request.model)
    
    except Exception as e:
        logger.exception("Completion failed")
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_completion_response(
    engine,
    prompt: str,
    sampling_params: SamplingParams,
    request_id: str,
    model: str,
):
    """Stream completion response."""
    created = int(time.time())
    
    async for output in await engine.generate_stream(
        prompt=prompt,
        sampling_params=sampling_params,
        request_id=request_id,
    ):
        for output_item in output.outputs:
            chunk = {
                "id": request_id,
                "object": "text_completion",
                "created": created,
                "model": model,
                "choices": [{
                    "index": output_item.index,
                    "text": output_item.text,
                    "finish_reason": output_item.finish_reason,
                }]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    
    yield "data: [DONE]\n\n"


def _build_completion_response(output, request_id: str, model: str) -> CompletionResponse:
    """Build completion response from engine output."""
    choices = []
    for output_item in output.outputs:
        choice = CompletionChoice(
            index=output_item.index,
            text=output_item.text,
            finish_reason=output_item.finish_reason,
        )
        choices.append(choice)
    
    usage = Usage(
        prompt_tokens=len(output.prompt_token_ids),
        completion_tokens=sum(len(o.token_ids) for o in output.outputs),
        total_tokens=len(output.prompt_token_ids) + sum(len(o.token_ids) for o in output.outputs),
    )
    
    return CompletionResponse(
        id=request_id,
        created=int(time.time()),
        model=model,
        choices=choices,
        usage=usage,
    )


@api_router.post("/tokenize")
async def tokenize(request: Request) -> Dict[str, Any]:
    """Tokenize text."""
    _check_api_key(request)
    
    body = await request.json()
    text = body.get("text", "")
    
    engine = get_engine()
    token_ids = await engine.tokenize(text)
    
    return {"token_ids": token_ids, "count": len(token_ids)}


@api_router.post("/detokenize")
async def detokenize(request: Request) -> Dict[str, Any]:
    """Detokenize token IDs."""
    _check_api_key(request)
    
    body = await request.json()
    token_ids = body.get("token_ids", [])
    
    engine = get_engine()
    text = await engine.detokenize(token_ids)
    
    return {"text": text}


@api_router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    engine = get_engine()
    if await engine.is_healthy():
        return {"status": "healthy"}
    return {"status": "unhealthy"}


@api_router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """Readiness check endpoint."""
    engine = get_engine()
    if await engine.is_healthy():
        return {"status": "ready"}
    return {"status": "not ready"}
