"""vLLM Engine wrapper with Data Parallel support."""

import inspect
import logging
import os
import torch
from typing import Any, AsyncGenerator, Dict, List, Optional

from vllm import SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.outputs import RequestOutput

from vllm_service.config import settings

logger = logging.getLogger(__name__)

# Checked once at first engine init; avoids repeated introspection per request.
_dp_args_supported: bool | None = None


def _check_dp_support() -> bool:
    global _dp_args_supported
    if _dp_args_supported is None:
        _dp_args_supported = (
            "data_parallel_size" in inspect.signature(AsyncEngineArgs.__init__).parameters
        )
    return _dp_args_supported


class VLLMEngineWrapper:
    """Wrapper for vLLM AsyncLLMEngine with Data Parallel support."""

    def __init__(self) -> None:
        self.engine: Optional[AsyncLLMEngine] = None
        self.model_name: str = os.environ.get(
            "VLLM_MODEL_NAME",
            settings.get("MODEL.model_name", "Qwen/Qwen2.5-7B-Instruct"),
        )
        self._initialized: bool = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        logger.info("Initializing vLLM engine with model: %s", self.model_name)
        engine_args = self._build_engine_args()
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self._initialized = True
        logger.info("vLLM engine initialized successfully")

    def _resolve_dtype(self, dtype: str) -> str:
        """Fall back from bfloat16 to float16 on GPUs with compute < 8.0 (pre-Ampere)."""
        if dtype not in ("auto", "bfloat16") or not torch.cuda.is_available():
            return dtype
        major, minor = torch.cuda.get_device_capability()
        if major < 8:
            logger.warning(
                "GPU compute capability %d.%d does not support bfloat16 "
                "(requires >= 8.0); using float16 instead",
                major, minor,
            )
            return "float16"
        return dtype

    def _build_engine_args(self) -> AsyncEngineArgs:
        data_parallel_size = int(settings.get("DATA_PARALLEL.data_parallel_size", 1) or 1)

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "dtype": self._resolve_dtype(settings.get("MODEL.model_dtype", "auto")),
            "max_model_len": int(settings.get("MODEL.max_model_len", 4096)),
            "gpu_memory_utilization": float(settings.get("MODEL.gpu_memory_utilization", 0.9)),
            "tensor_parallel_size": int(settings.get("ENGINE.tensor_parallel_size", 1)),
            "max_num_seqs": int(settings.get("ENGINE.max_num_seqs", 256)),
        }

        max_batched = settings.get("ENGINE.max_num_batched_tokens")
        if max_batched:
            kwargs["max_num_batched_tokens"] = int(max_batched)

        if data_parallel_size > 1:
            if _check_dp_support():
                kwargs.update({
                    "data_parallel_size": data_parallel_size,
                    "data_parallel_rank": int(
                        settings.get("DATA_PARALLEL.data_parallel_rank") or 0
                    ),
                    "data_parallel_address": settings.get(
                        "DATA_PARALLEL.data_parallel_address", "localhost"
                    ),
                    "data_parallel_rpc_port": int(
                        settings.get("DATA_PARALLEL.data_parallel_rpc_port") or 13345
                    ),
                    "data_parallel_size_local": int(
                        settings.get("DATA_PARALLEL.data_parallel_size_local") or 1
                    ),
                })
                logger.info(
                    "Configuring Data Parallel: size=%d, rank=%d",
                    data_parallel_size,
                    kwargs["data_parallel_rank"],
                )
            else:
                logger.warning(
                    "Installed vLLM does not support data_parallel_size in AsyncEngineArgs "
                    "(requires vllm >= 0.6.x); running in single-engine mode"
                )

        return AsyncEngineArgs(**kwargs)

    async def generate(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        request_id: str,
    ) -> RequestOutput:
        if not self._initialized:
            await self.initialize()
        final_output: Optional[RequestOutput] = None
        async for output in self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        ):
            final_output = output
        return final_output

    async def generate_stream(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        request_id: str,
    ) -> AsyncGenerator[RequestOutput, None]:
        if not self._initialized:
            await self.initialize()
        async for output in self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        ):
            yield output

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        sampling_params: SamplingParams,
        request_id: str,
        chat_template: Optional[str] = None,
    ) -> RequestOutput:
        if not self._initialized:
            await self.initialize()
        prompt = self._messages_to_prompt(messages, chat_template)
        final_output: Optional[RequestOutput] = None
        async for output in self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        ):
            final_output = output
        return final_output

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        sampling_params: SamplingParams,
        request_id: str,
        chat_template: Optional[str] = None,
    ) -> AsyncGenerator[RequestOutput, None]:
        if not self._initialized:
            await self.initialize()
        prompt = self._messages_to_prompt(messages, chat_template)
        async for output in self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        ):
            yield output

    def _messages_to_prompt(
        self,
        messages: List[Dict[str, Any]],
        chat_template: Optional[str] = None,
    ) -> str:
        parts: List[str] = []
        if chat_template:
            parts.append(f"system: {chat_template}")

        for m in messages:
            role = m.get("role", "user").lower()
            content = m.get("content")
            if content is None:
                continue
            if role not in {"system", "user", "assistant"}:
                role = "user"
            parts.append(f"{role}: {str(content).strip()}")

        parts.append("assistant:")
        return "\n".join(parts)

    async def tokenize(self, text: str) -> List[int]:
        if not self._initialized:
            await self.initialize()
        return self.engine.tokenizer.encode(text)

    async def detokenize(self, token_ids: List[int]) -> str:
        if not self._initialized:
            await self.initialize()
        return self.engine.tokenizer.decode(token_ids)

    async def get_model_config(self) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        return self.engine.engine.model_config.hf_config.to_dict()

    async def is_healthy(self) -> bool:
        return self._initialized and self.engine is not None

    async def shutdown(self) -> None:
        if not self.engine:
            return
        logger.info("Shutting down vLLM engine")
        try:
            shutdown_fn = getattr(self.engine, "shutdown", None)
            if shutdown_fn is not None:
                if inspect.iscoroutinefunction(shutdown_fn):
                    await shutdown_fn()
                else:
                    shutdown_fn()
        except Exception as exc:
            logger.warning("Exception during AsyncLLMEngine.shutdown: %s", exc)
        finally:
            self._initialized = False
            self.engine = None
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception as exc:
                logger.debug("Failed to empty CUDA cache: %s", exc)


_engine: Optional[VLLMEngineWrapper] = None


def get_engine() -> VLLMEngineWrapper:
    global _engine
    if _engine is None:
        _engine = VLLMEngineWrapper()
    return _engine


async def initialize_engine() -> None:
    await get_engine().initialize()


async def shutdown_engine() -> None:
    global _engine
    if _engine:
        await _engine.shutdown()
        _engine = None
