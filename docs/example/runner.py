from agents import Runner as ExternalRunner
from agents.exceptions import MaxTurnsExceeded
import asyncio
import logging
import inspect
from service.settings import config

logger = logging.getLogger(__name__)


async def _iterate_and_normalize(aiterable):
    seq_counter = 0
    async for raw in aiterable:
        seq_counter += 1
        if isinstance(raw, dict):
            yield {
                "seq": raw.get("seq", seq_counter),
                "data": raw.get("data", ""),
                "metadata": raw.get("metadata", None),
            }
        else:
            yield {"seq": seq_counter, "data": str(raw), "metadata": None}


async def _extract_final(r):
    if r is None:
        return None
    for attr in ("final_output", "output", "response", "_final_output"):
        try:
            v = getattr(r, attr, None)
        except Exception:
            v = None
        if v is not None:
            if hasattr(v, "text"):
                return getattr(v, "text")
            if hasattr(v, "__root__"):
                return getattr(v, "__root__")
            return v
    try:
        if hasattr(r, "get_final_output") and callable(r.get_final_output):
            maybe = r.get_final_output()
            if hasattr(maybe, "__await__"):
                return await maybe  # type: ignore
            return maybe
    except Exception:
        pass
    return None



class Runner:
    @staticmethod
    async def run(starting_agent, input, context=None, max_turns=None):
        if ExternalRunner is None or not hasattr(ExternalRunner, "run"):
            logger.error("Runner.run: ExternalRunner.run is not available; cannot execute agent")
            raise RuntimeError("ExternalRunner.run is not available; ensure the agents package is installed and provides Runner.run")
        logger.debug("Runner.run: invoking ExternalRunner.run (context_type=%s) starting_agent=%s input_preview=%s", type(context), getattr(starting_agent, 'name', str(starting_agent)), (str(input)[:200] if input is not None else None))
        # Determine default max_turns from central config if not provided
        env_default = getattr(config, "agent_max_turns", 10)
        use_max = max_turns if max_turns is not None else env_default

        # Call ExternalRunner.run, passing max_turns if the SDK supports it
        try:
            sig = inspect.signature(ExternalRunner.run)
            if 'max_turns' in sig.parameters:
                return await ExternalRunner.run(starting_agent, input, context=context, max_turns=use_max)
        except Exception:
            # If introspection fails, fall back to calling without the kwarg
            pass

        return await ExternalRunner.run(starting_agent, input, context=context)

    @staticmethod
    async def stream(starting_agent, input, context=None):
        if ExternalRunner is None:
            logger.error("Runner.stream: ExternalRunner is not available; cannot stream")
            raise RuntimeError("ExternalRunner is not available; ensure the agents package is installed and provides Runner")

        try:
            agent_name = getattr(starting_agent, "name", "") or ""
        except Exception:
            agent_name = ""

        if hasattr(ExternalRunner, "run_streamed"):
            two_phase_flag = False
            try:
                two_phase_flag = bool(getattr(starting_agent, "two_phase", False))
            except Exception:
                two_phase_flag = False
            try:
                cfg_list = getattr(config, "agents_two_phase", []) or []
            except Exception:
                cfg_list = []
            if two_phase_flag or (agent_name in cfg_list) or "MealCalendar" in agent_name or "meal_calendar" in agent_name.lower():
                logger.debug("Runner.stream: detected two_phase agent; using two-phase flow")
                try:
                    run_result = await Runner.run(starting_agent, input, context)
                except Exception:
                    logger.exception("Runner.stream: non-streamed run (phase 1) failed for %s", agent_name)
                    raise
                try:
                    final_struct = await _extract_final(run_result)
                except Exception:
                    logger.exception("Runner.stream: failed to extract final structured output after non-streamed run")
                    final_struct = None
                seq = 0
                if final_struct is not None:
                    seq += 1
                    yield {"seq": seq, "data": final_struct, "metadata": {"stream_event_type": "final_output", "final_output": final_struct}}
                try:
                    from agents import Agent as SDK_Agent
                except Exception:
                    SDK_Agent = None
                if SDK_Agent is not None:
                    try:
                        narrator_instructions = (
                            "You are a friendly assistant. Do NOT call any tools.\n"
                            "You have been provided with a generated meal calendar in the conversation context.\n"
                            "Produce a concise, human-friendly explanation of the plan (3-4 short sentences). Do not attempt any external lookups or tool calls."
                        )
                        model_obj = getattr(starting_agent, "model", None)
                        model_settings_obj = getattr(starting_agent, "model_settings", None)
                        narrator_model_settings = None
                        try:
                            from agents import ModelSettings as SDK_ModelSettings
                            try:
                                narrator_model_settings = SDK_ModelSettings(temperature=0.2, max_tokens=250)
                            except Exception:
                                try:
                                    narrator_model_settings = SDK_ModelSettings(temperature=0.2)
                                    if hasattr(narrator_model_settings, "max_tokens"):
                                        try:
                                            setattr(narrator_model_settings, "max_tokens", 250)
                                        except Exception:
                                            pass
                                except Exception:
                                    narrator_model_settings = model_settings_obj
                        except Exception:
                            try:
                                if model_settings_obj is not None and hasattr(model_settings_obj, "model_copy"):
                                    narrator_model_settings = model_settings_obj.model_copy(deep=False)
                                else:
                                    narrator_model_settings = model_settings_obj
                            except Exception:
                                narrator_model_settings = model_settings_obj
                        narrator_agent = SDK_Agent(name=f"{agent_name}-Narrator", instructions=narrator_instructions, model=model_obj, model_settings=narrator_model_settings, tools=[])
                        try:
                            from agents import RunContextWrapper as SDK_RunContextWrapper
                            import json as _json
                            if isinstance(final_struct, str):
                                try:
                                    payload_extra = _json.loads(final_struct)
                                except Exception:
                                    payload_extra = final_struct
                            else:
                                payload_extra = final_struct
                            try:
                                ctx_payload = context.model_dump() if hasattr(context, "model_dump") else (context.dict() if hasattr(context, "dict") else context)
                            except Exception:
                                ctx_payload = context
                            if isinstance(ctx_payload, dict):
                                ctx_payload = dict(ctx_payload)
                                ctx_payload["generated_calendar"] = payload_extra
                            else:
                                ctx_payload = {"context": ctx_payload, "generated_calendar": payload_extra}
                            narrator_ctx = SDK_RunContextWrapper(ctx_payload)
                        except Exception:
                            narrator_ctx = None
                        if narrator_ctx is not None:
                            try:
                                env_default = getattr(config, "agent_max_turns", 10)
                                try:
                                    narrator_max_turns = min(3, env_default) if isinstance(env_default, int) else 3
                                    sig = inspect.signature(ExternalRunner.run_streamed)
                                    if 'max_turns' in sig.parameters:
                                        narrator_result = ExternalRunner.run_streamed(narrator_agent, "Please narrate the generated plan to the user.", narrator_ctx, max_turns=narrator_max_turns)
                                    else:
                                        narrator_result = ExternalRunner.run_streamed(narrator_agent, "Please narrate the generated plan to the user.", narrator_ctx)
                                except Exception:
                                    narrator_result = ExternalRunner.run_streamed(narrator_agent, "Please narrate the generated plan to the user.", narrator_ctx)
                                async for event in narrator_result.stream_events():
                                    seq += 1
                                    etype = getattr(event, "type", None)
                                    data = None
                                    metadata = {"stream_event_type": etype}
                                    if etype == "raw_response_event":
                                        raw = getattr(event, "data", None)
                                        delta = getattr(raw, "delta", None)
                                        data = delta if delta is not None else str(raw)
                                    else:
                                        data = str(event)
                                    try:
                                        logger.debug("Runner.stream narrator event seq=%s type=%s data_preview=%s", seq, etype, (str(data)[:200] if data is not None else None))
                                    except Exception:
                                        logger.debug("Runner.stream narrator event seq=%s type=%s (format failed)", seq, etype)
                                    yield {"seq": seq, "data": data, "metadata": metadata}
                            except Exception:
                                logger.exception("Runner.stream: narrator run_streamed failed")
                    except Exception:
                        logger.exception("Runner.stream: failed to construct/run narrator agent")
                return
        if hasattr(ExternalRunner, "run_streamed"):
            logger.debug("Runner.stream: using ExternalRunner.run_streamed starting_agent=%s context_type=%s", getattr(starting_agent, 'name', str(starting_agent)), type(context))
            env_default = getattr(config, "agent_max_turns", 10)
            try:
                sig = inspect.signature(ExternalRunner.run_streamed)
                if 'max_turns' in sig.parameters:
                    result = ExternalRunner.run_streamed(starting_agent, input, context, max_turns=env_default)
                else:
                    result = ExternalRunner.run_streamed(starting_agent, input, context)
            except Exception:
                result = ExternalRunner.run_streamed(starting_agent, input, context)
            seq = 0
            try:
                async for event in result.stream_events():
                    seq += 1
                    try:
                        env_default = getattr(config, "agent_max_turns", 10)
                        threshold = max(500, min(5000, env_default * 50))
                    except Exception:
                        threshold = 1000
                    if seq > threshold:
                        logger.error("Runner.stream: processed %s events, exceeding threshold %s; attempting best-effort final extraction and terminating stream", seq, threshold)
                        try:
                            close_m = getattr(result, "aclose", None) or getattr(result, "close", None) or getattr(result, "cancel", None)
                            if close_m is not None:
                                maybe = close_m()
                                if hasattr(maybe, "__await__"):
                                    await maybe  # type: ignore
                        except Exception:
                            logger.debug("Runner.stream: closing result failed or not supported")
                        try:
                            final = await _extract_final(result)
                            if final is not None:
                                seq += 1
                                yield {"seq": seq, "data": final, "metadata": {"stream_event_type": "final_output", "final_output": final, "reason": "threshold_exceeded"}}
                                return
                        except Exception:
                            logger.exception("Runner.stream: failed to extract final_output after threshold exceeded")
                        seq += 1
                        yield {"seq": seq, "data": {"error": "threshold_exceeded", "threshold": threshold}, "metadata": {"stream_event_type": "final_output", "reason": "threshold_exceeded"}}
                        return
                    etype = getattr(event, "type", None)
                    data = None
                    metadata = {"stream_event_type": etype}
                    if etype == "raw_response_event":
                        raw = getattr(event, "data", None)
                        delta = getattr(raw, "delta", None)
                        data = delta if delta is not None else str(raw)
                        try:
                            logger.warning("Runner.stream raw_response_event seq=%s delta=%s full=%s", seq, (str(delta)[:200] if delta is not None else None), (str(raw)[:500] if raw is not None else None))
                        except Exception:
                            logger.debug("Runner.stream raw_response_event logging failed for seq=%s", seq)
                    elif etype == "run_item_stream_event":
                        item = getattr(event, "item", None)
                        if item is not None:
                            out = getattr(item, "output", None) or getattr(item, "text", None)
                            data = out if out is not None else str(item)
                            metadata["item_type"] = getattr(item, "type", None)
                            try:
                                item_agent = getattr(item, "agent", None)
                                agent_name = getattr(item_agent, "name", None) if item_agent is not None else None
                                current_turn = getattr(item, "current_turn", None)
                                max_turns_item = getattr(item, "max_turns", None)
                                is_complete = getattr(item, "is_complete", None)
                                tool_name = None
                                tool = getattr(item, "tool", None) or getattr(item, "tool_name", None)
                                if tool is not None:
                                    tool_name = getattr(tool, "name", str(tool))
                                metadata.update({"agent_name": agent_name, "current_turn": current_turn, "max_turns_item": max_turns_item, "is_complete": is_complete, "tool_name": tool_name})
                                logger.warning("Runner.stream run_item seq=%s agent=%s turn=%s/%s complete=%s tool=%s data_preview=%s", seq, agent_name, current_turn, max_turns_item, is_complete, tool_name, (str(data)[:200] if data is not None else None))
                            except Exception:
                                logger.debug("Runner.stream run_item_stream_event logging failed for seq=%s", seq)
                        else:
                            data = str(event)
                    elif etype == "agent_updated_stream_event":
                        new_agent = getattr(event, "new_agent", None)
                        data = f"agent_updated:{getattr(new_agent, 'name', str(new_agent))}"
                        metadata["new_agent_name"] = getattr(new_agent, "name", None)
                        try:
                            logger.warning("Runner.stream agent_updated seq=%s new_agent=%s", seq, getattr(new_agent, 'name', str(new_agent)))
                        except Exception:
                            logger.debug("Runner.stream agent_updated logging failed for seq=%s", seq)
                    else:
                        data = str(event)
                    try:
                        logger.debug("Runner.stream event seq=%s type=%s data_preview=%s", seq, etype, (str(data)[:200] if data is not None else None))
                    except Exception:
                        logger.debug("Runner.stream event seq=%s type=%s (format failed)", seq, etype)
                    yield {"seq": seq, "data": data, "metadata": metadata}
                try:
                    final = None
                    try:
                        maybe = _extract_final(result)
                        if hasattr(maybe, "__await__"):
                            final = await maybe  # type: ignore
                        else:
                            final = maybe
                    except Exception:
                        logger.exception("Runner.stream failed while extracting final_output")
                    if final is not None:
                        seq += 1
                        yield {"seq": seq, "data": final, "metadata": {"stream_event_type": "final_output", "final_output": final}}
                except Exception:
                    logger.exception("Runner.stream failed to extract final_output")
                return
            except Exception as exc:
                if MaxTurnsExceeded is not None and isinstance(exc, MaxTurnsExceeded):
                    logger.error("Runner.stream: ExternalRunner.run_streamed raised MaxTurnsExceeded: %s", exc)
                    try:
                        close_m = getattr(result, "aclose", None) or getattr(result, "close", None) or getattr(result, "cancel", None)
                        if close_m is not None:
                            maybe = close_m()
                            if hasattr(maybe, "__await__"):
                                await maybe  # type: ignore
                    except Exception:
                        logger.debug("Runner.stream: closing result failed or not supported after MaxTurnsExceeded")
                    try:
                        final = None
                        try:
                            maybe = _extract_final(result)
                            if hasattr(maybe, "__await__"):
                                final = await maybe  # type: ignore
                            else:
                                final = maybe
                        except Exception:
                            logger.exception("Runner.stream: failed while extracting final_output after MaxTurnsExceeded")
                        if final is not None:
                            seq += 1
                            yield {"seq": seq, "data": final, "metadata": {"stream_event_type": "final_output", "final_output": final, "reason": "max_turns_exceeded"}}
                            return
                    except Exception:
                        logger.exception("Runner.stream: failed to recover final_output after MaxTurnsExceeded")
                    seq += 1
                    yield {"seq": seq, "data": {"error": "max_turns_exceeded", "message": str(exc)}, "metadata": {"stream_event_type": "final_output", "reason": "max_turns_exceeded"}}
                    return
                logger.exception("Error while iterating run_streamed events")
                raise
        if hasattr(ExternalRunner, "stream"):
            logger.debug("Runner.stream: using ExternalRunner.stream starting_agent=%s context_type=%s", getattr(starting_agent, 'name', str(starting_agent)), type(context))
            aiter = ExternalRunner.stream(starting_agent, input, context)
            async for c in _iterate_and_normalize(aiter):
                logger.debug("Runner.stream (external.stream) yielding seq=%s", c.get('seq'))
                yield c
            return
        logger.error("Runner.stream: no streaming API available on ExternalRunner; cannot stream")
        raise RuntimeError("ExternalRunner does not expose streaming APIs (run_streamed/stream)")
