"""vLLM Engine wrapper with Data Parallel support."""

import logging
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
        self.model_name: str = settings.get("model_name", "Qwen/Qwen2.5-7B-Instruct")
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
        data_parallel_size = int(settings.get("data_parallel_size", 1))
        data_parallel_rank = int(settings.get("data_parallel_rank", 0))
        data_parallel_address = settings.get("data_parallel_address", "localhost")
        data_parallel_rpc_port = int(settings.get("data_parallel_rpc_port", 13345))
        data_parallel_size_local = int(settings.get("data_parallel_size_local", 1))
        
        # Build AsyncEngineArgs for async engine
        engine_args = AsyncEngineArgs(
            model=self.model_name,
            dtype=settings.get("model_dtype", "auto"),
            max_model_len=int(settings.get("max_model_len", 4096)),
            gpu_memory_utilization=float(settings.get("gpu_memory_utilization", 0.9)),
            tensor_parallel_size=int(settings.get("tensor_parallel_size", 1)),
            max_num_seqs=int(settings.get("max_num_seqs", 256)),
            max_num_batched_tokens=int(settings.get("max_num_batched_tokens", 8192)) if settings.get("max_num_batched_tokens") else None,
            data_parallel_size=data_parallel_size if data_parallel_size > 1 else None,
            data_parallel_rank=data_parallel_rank if data_parallel_size > 1 else None,
            data_parallel_address=data_parallel_address if data_parallel_size > 1 else None,
            data_parallel_rpc_port=data_parallel_rpc_port if data_parallel_size > 1 else None,
            data_parallel_size_local=data_parallel_size_local if data_parallel_size > 1 else None,
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
        
        # Use vLLM's chat capability
        results_generator = self.engine.chat(
            messages=messages,
            sampling_params=sampling_params,
            request_id=request_id,
            chat_template=chat_template,
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
        
        results_generator = self.engine.chat(
            messages=messages,
            sampling_params=sampling_params,
            request_id=request_id,
            chat_template=chat_template,
        )
        
        async for output in results_generator:
            yield output

    async def tokenize(self, text: str) -> List[int]:
        """Tokenize text."""
        if not self._initialized:
            await self.initialize()
        
        # Get tokenizer from engine
        tokenizer = self.engine.engine.tokenizer
        return tokenizer.encode(text)

    async def detokenize(self, token_ids: List[int]) -> str:
        """Detokenize token IDs."""
        if not self._initialized:
            await self.initialize()
        
        tokenizer = self.engine.engine.tokenizer
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
            self._initialized = False
            self.engine = None


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
