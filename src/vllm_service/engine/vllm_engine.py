"""vLLM Engine wrapper with Data Parallel support."""

import logging
import os
import torch
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from vllm import SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.outputs import RequestOutput

from vllm_service.config import settings

logger = logging.getLogger(__name__)


class VLLMEngineWrapper:
    """Wrapper for vLLM AsyncLLMEngine with Data Parallel support."""

    def __init__(self) -> None:
        """Initialize the vLLM engine with Data Parallel configuration."""
        self.engine: Optional[AsyncLLMEngine] = None
        self.model_name: str = os.environ.get("VLLM_MODEL_NAME", settings.get("MODEL.model_name", settings.get("model_name", "Qwen/Qwen2.5-7B-Instruct")))
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize the engine asynchronously."""
        if self._initialized:
            return

        logger.info(f"Initializing vLLM engine with model: {self.model_name}")
        engine_args = self._build_engine_args()
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self._initialized = True
        logger.info("vLLM engine initialized successfully")

    def _build_engine_args(self) -> AsyncEngineArgs:
        """Build engine arguments from settings."""
        # Get all settings with defaults
        data_parallel_size = int(settings.get("DATA_PARALLEL.data_parallel_size", 1) or 1)
        data_parallel_rank = settings.get("DATA_PARALLEL.data_parallel_rank")
        data_parallel_address = settings.get("DATA_PARALLEL.data_parallel_address", "localhost")
        data_parallel_rpc_port = settings.get("DATA_PARALLEL.data_parallel_rpc_port", 13345)
        data_parallel_size_local = settings.get("DATA_PARALLEL.data_parallel_size_local", 1)

        if data_parallel_size <= 1:
            # For single-node mode, disable external load-balancing flags by
            # leaving rank/address/rpc as None.
            data_parallel_rank = None
            data_parallel_address = None
            data_parallel_rpc_port = None
            data_parallel_size_local = None
        else:
            data_parallel_rank = int(data_parallel_rank or 0)
            data_parallel_rpc_port = int(data_parallel_rpc_port or 13345)
            data_parallel_size_local = int(data_parallel_size_local or 1)
        
        # Build AsyncEngineArgs for async engine
        engine_args = AsyncEngineArgs(
            model=self.model_name,
            dtype=settings.get("MODEL.model_dtype", "auto"),
            max_model_len=int(settings.get("MODEL.max_model_len", 4096)),
            gpu_memory_utilization=float(settings.get("MODEL.gpu_memory_utilization", 0.9)),
            tensor_parallel_size=int(settings.get("ENGINE.tensor_parallel_size", 1)),
            max_num_seqs=int(settings.get("ENGINE.max_num_seqs", 256)),
            max_num_batched_tokens=int(settings.get("ENGINE.max_num_batched_tokens", 8192)) if settings.get("ENGINE.max_num_batched_tokens") else None,
            data_parallel_size=data_parallel_size,
            data_parallel_rank=data_parallel_rank,
            data_parallel_address=data_parallel_address,
            data_parallel_rpc_port=data_parallel_rpc_port,
            data_parallel_size_local=data_parallel_size_local,
        )
        
        if data_parallel_size > 1:
            logger.info(f"Configuring Data Parallel: size={data_parallel_size}, rank={data_parallel_rank}")
        
        return engine_args

    async def generate(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        request_id: str,
    ) -> RequestOutput:
        """Generate text for a single prompt."""
        if not self._initialized:
            await self.initialize()
        
        results_generator = self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        )
        
        final_output: Optional[RequestOutput] = None
        async for output in results_generator:
            final_output = output
        
        return final_output

    async def generate_stream(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        request_id: str,
    ) -> AsyncGenerator[RequestOutput, None]:
        """Generate text with streaming."""
        if not self._initialized:
            await self.initialize()
        
        results_generator = self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        )
        
        async for output in results_generator:
            yield output

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        sampling_params: SamplingParams,
        request_id: str,
        chat_template: Optional[str] = None,
    ) -> RequestOutput:
        """Generate chat completion."""
        if not self._initialized:
            await self.initialize()
        prompt = self._messages_to_prompt(messages, chat_template)
        # Use vLLM's chat capability via text generation prompt
        results_generator = self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        )
        
        final_output: Optional[RequestOutput] = None
        async for output in results_generator:
            final_output = output
        
        return final_output

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        sampling_params: SamplingParams,
        request_id: str,
        chat_template: Optional[str] = None,
    ) -> AsyncGenerator[RequestOutput, None]:
        """Generate chat completion with streaming."""
        if not self._initialized:
            await self.initialize()
        prompt = self._messages_to_prompt(messages, chat_template)
        results_generator = self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        )
        
        async for output in results_generator:
            yield output

    def _messages_to_prompt(self, messages: List[Dict[str, Any]], chat_template: Optional[str] = None) -> str:
        """Convert chat messages to a single prompt string."""
        formatted = []
        if chat_template:
            formatted.append(f"system: {chat_template}")

        for m in messages:
            role = m.get("role", "user").lower()
            content = m.get("content", "")
            if content is None:
                continue

            if role not in {"system", "user", "assistant"}:
                role = "user"

            # OpenAI style role prefixes.
            formatted.append(f"{role}: {content.strip()}")

        # Always generate assistant message after last user turn.
        if messages and messages[-1].get("role", "user").lower() == "user":
            formatted.append("assistant:")
        else:
            # For safety in dialogue continuation, always include assistant slot.
            formatted.append("assistant:")

        return "\n".join(formatted)

    async def tokenize(self, text: str) -> List[int]:
        """Tokenize text."""
        if not self._initialized:
            await self.initialize()
        
        # Get tokenizer from AsyncLLMEngine
        tokenizer = self.engine.tokenizer
        return tokenizer.encode(text)

    async def detokenize(self, token_ids: List[int]) -> str:
        """Detokenize token IDs."""
        if not self._initialized:
            await self.initialize()
        
        tokenizer = self.engine.tokenizer
        return tokenizer.decode(token_ids)

    async def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration."""
        if not self._initialized:
            await self.initialize()
        
        return self.engine.engine.model_config.hf_config.to_dict()

    async def is_healthy(self) -> bool:
        """Check if engine is healthy."""
        return self._initialized and self.engine is not None

    async def shutdown(self) -> None:
        """Shutdown the engine."""
        if self.engine:
            # vLLM engine cleanup
            logger.info("Shutting down vLLM engine")
            try:
                await self.engine.shutdown()
            except Exception as e:
                logger.warning("Exception during AsyncLLMEngine.shutdown: %s", e)
            self._initialized = False
            self.engine = None

            # Release CUDA memory if available.
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception as e:
                logger.debug("Failed to empty CUDA cache: %s", e)


_engine: Optional[VLLMEngineWrapper] = None


def get_engine() -> VLLMEngineWrapper:
    """Get or create the global engine instance."""
    global _engine
    if _engine is None:
        _engine = VLLMEngineWrapper()
    return _engine


async def initialize_engine() -> None:
    """Initialize the global engine."""
    engine = get_engine()
    await engine.initialize()


async def shutdown_engine() -> None:
    """Shutdown the global engine."""
    global _engine
    if _engine:
        await _engine.shutdown()
        _engine = None
