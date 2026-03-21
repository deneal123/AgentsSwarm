"""vLLM Engine wrapper with Data Parallel support."""

import argparse
import asyncio
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from vllm import SamplingParams
from vllm.engine.arg_utils import EngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.outputs import RequestOutput

from vllm_service.config.config import settings

logger = logging.getLogger(__name__)


class VLLMEngineWrapper:
    """Wrapper for vLLM AsyncLLMEngine with Data Parallel support."""

    def __init__(self) -> None:
        """Initialize the vLLM engine with Data Parallel configuration."""
        self.engine: Optional[AsyncLLMEngine] = None
        self.model_name: str = settings.model.model_name
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

    def _build_engine_args(self) -> EngineArgs:
        """Build engine arguments from settings."""
        data_parallel_size = int(settings.data_parallel.get("data_parallel_size", 1))
        data_parallel_rank = int(settings.data_parallel.get("data_parallel_rank", 0))
        data_parallel_address = settings.data_parallel.get("data_parallel_address", "localhost")
        data_parallel_rpc_port = int(settings.data_parallel.get("data_parallel_rpc_port", 13345))
        data_parallel_size_local = int(settings.data_parallel.get("data_parallel_size_local", 1))
        
        args = [
            "--model", self.model_name,
            "--dtype", str(settings.model.get("model_dtype", "auto")),
            "--max-model-len", str(settings.mdoel.get("max_model_len", 4096)),
            "--gpu-memory-utilization", str(settings.model.get("gpu_memory_utilization", 0.9)),
            "--tensor-parallel-size", str(settings.engine.get("tensor_parallel_size", 1)),
            "--max-num-seqs", str(settings.engine.get("max_num_seqs", 256)),
        ]
        
        if settings.engine.get("max_num_batched_tokens"):
            args.extend(["--max-num-batched-tokens", str(settings.engine.max_num_batched_tokens)])
        
        if data_parallel_size > 1:
            logger.info(f"Configuring Data Parallel: size={data_parallel_size}, rank={data_parallel_rank}")
            args.extend([
                "--data-parallel-size", str(data_parallel_size),
                "--data-parallel-rank", str(data_parallel_rank),
                "--data-parallel-address", data_parallel_address,
                "--data-parallel-rpc-port", str(data_parallel_rpc_port),
                "--data-parallel-size-local", str(data_parallel_size_local),
            ])
            
            if data_parallel_rank > 0:
                args.append("--headless")
        
        parser = EngineArgs.add_cli_args(argparse.ArgumentParser())
        parsed_args = parser.parse_args(args)
        
        return EngineArgs.from_cli_args(parsed_args)

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
