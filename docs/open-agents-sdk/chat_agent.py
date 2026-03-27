from typing import Optional, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ChatAgent:
    """Thin chat agent wrapper that delegates to Orchestrator/Runner.

    The orchestrator routes the request to a specialized agent (nutrition, meal_calendar, etc.).
    This method executes the chosen agent (via Runner.run) and returns a structured response
    containing 'reply' and optional 'metadata' with an explicit action schema, e.g.
    metadata={"action": {"type": "calendar.create", "payload": {...}}}

    The contract remains async to allow session writes.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

    async def handle_message(self, thread_id: int | str, text: str, user_id: Optional[int] = None, session: Optional[Any] = None) -> dict:
        # Lazy import required agent components. Fail fast on missing modules to avoid
        # hidden legacy fallbacks.
        try:
            from service.agents.scripts.orchestrator import OrchestratorAgent
            from service.agents.runner import Runner
            from service.agents.pydantic.agents import UserContext, MealCalendarOutput
        except Exception:
            logger.exception("ChatAgent: required agent modules not available")
            raise

        # Streaming-first: do not provide legacy echo fallback. Fail loudly so callers
        # must use the supported Runner/RunContextWrapper contract.
        reply_text = None
        metadata: dict = {}

        try:
            # Build context (Pydantic UserContext) and normalize for Runner
            # Ensure we always have a conversation session object (create if missing) and embed
            # session_id/session_store metadata into UserContext. This removes legacy fallbacks
            # where callers could omit session and various wrapper fallbacks were attempted.
            context = None
            try:
                # If no conversation session provided, create one deterministically from user/thread
                if session is None:
                    try:
                        from service.agents.sessions import create_session
                        # Use composite id so different threads have distinct conversation sessions
                        session_key = f"{str(user_id or 'anon')}-{str(thread_id)}"
                        session = create_session(session_key)
                    except Exception:
                        # If creation fails, keep session None (but we still enforce context below)
                        session = None

                # Prepare session metadata for context
                session_id_for_ctx = None
                session_store_info = None
                try:
                    if session is not None:
                        session_id_for_ctx = getattr(session, "session_id", None) or getattr(session, "session_id", None)
                        session_store_info = {
                            "type": session.__class__.__name__,
                            "has_add_items": hasattr(session, "add_items"),
                        }
                except Exception:
                    session_id_for_ctx = None
                    session_store_info = None

                # Build pydantic UserContext. We now require at least an empty session_id to be present
                context = UserContext(
                    user_id=str(user_id or ""),
                    request_time=datetime.now(timezone.utc),
                    previous_questions=None,
                    session=session,
                    session_id=str(session_id_for_ctx) if session_id_for_ctx is not None else None,
                    session_store=session_store_info,
                )

            except Exception:
                # Fail hard on context construction to avoid silent fallbacks - caller should provide valid inputs
                logger.exception("ChatAgent: failed to construct required UserContext")
                raise

            # Log what we got for UserContext so we can debug failures to build context
            try:
                logger.warning("ChatAgent: built UserContext type=%s preview=%s", type(context), (str(context)[:300] if context is not None else None))
            except Exception:
                logger.exception("ChatAgent: failed to log UserContext")

            # Normalize context for the agents Runner: require RunContextWrapper from agents package.
            # Legacy behavior that tried many fallbacks is intentionally removed.
            try:
                from agents import RunContextWrapper  # type: ignore
            except Exception:
                logger.exception("ChatAgent: required agents.RunContextWrapper not available; cannot proceed")
                raise RuntimeError("agents.RunContextWrapper is required")

            try:
                ctx_payload = context.model_dump() if hasattr(context, "model_dump") else (context.dict() if hasattr(context, "dict") else context)
                rc = RunContextWrapper(ctx_payload)
                runner_context = rc
            except Exception:
                logger.exception("ChatAgent: failed to build RunContextWrapper from context")
                raise

            orchestrator = OrchestratorAgent(self.config.get("model_settings", {})) if OrchestratorAgent else None
            selected_agent = await orchestrator.route_request(text) if orchestrator else None

            if selected_agent is not None and Runner is not None:
                # If Runner exposes a streaming interface, publish chunks as they arrive
                try:
                    # import container module robustly (tests may inject into sys.modules)
                    import importlib
                    _container = importlib.import_module("service.container")
                    from service.infrastructure.messaging import stream_helpers as _sh
                    import json

                    def _make_serializable(obj):
                        # Recursively convert common non-serializable objects (pydantic models, namespaces) into JSONables
                        try:
                            if obj is None:
                                return None
                            if isinstance(obj, (str, int, float, bool)):
                                return obj
                            if isinstance(obj, dict):
                                return {k: _make_serializable(v) for k, v in obj.items()}
                            if isinstance(obj, (list, tuple)):
                                return [_make_serializable(v) for v in obj]
                            if hasattr(obj, "model_dump") and callable(obj.model_dump):
                                try:
                                    return _make_serializable(obj.model_dump())
                                except Exception:
                                    return str(obj)
                            if hasattr(obj, "dict") and callable(obj.dict):
                                try:
                                    return _make_serializable(obj.dict())
                                except Exception:
                                    return str(obj)
                            # fallback: try json dumping, otherwise string
                            try:
                                json.dumps(obj)
                                return obj
                            except Exception:
                                return str(obj)
                        except Exception:
                            return str(obj)

                    redis_client = None
                    try:
                        redis_client = _container.get(_container.RedisClientName)
                    except Exception:
                        redis_client = None

                    # Runner.stream is required in the new strict mode. Do not use legacy non-stream fallback.
                    if not hasattr(Runner, "stream"):
                        logger.error("ChatAgent: Runner.stream is required but not present")
                        raise RuntimeError("Runner.stream is required")

                    # Iterate and publish chunks from Runner.stream
                    # (no fallback to Runner.run allowed)
                    if hasattr(Runner, "stream"):
                        final_output = None
                        seq = 0

                        def _extract_action(data, metadata_chunk):
                            # prefer explicit action in metadata
                            try:
                                if isinstance(metadata_chunk, dict):
                                    a = metadata_chunk.get("action")
                                    if isinstance(a, dict):
                                        return a
                                    # some runners may put final_output in metadata
                                    if metadata_chunk.get("stream_event_type") == "final_output" and metadata_chunk.get("final_output"):
                                        fo = metadata_chunk.get("final_output")
                                        if isinstance(fo, dict) and fo.get("action"):
                                            return fo.get("action")
                            except Exception:
                                pass

                            # try inspecting data for action key (dict or JSON string)
                            try:
                                if isinstance(data, dict):
                                    if data.get("metadata") and isinstance(data.get("metadata"), dict):
                                        a = data["metadata"].get("action")
                                        if isinstance(a, dict):
                                            return a
                                    if data.get("action") and isinstance(data.get("action"), dict):
                                        return data.get("action")
                                if isinstance(data, str):
                                    import json as _json
                                    try:
                                        parsed = _json.loads(data)
                                        if isinstance(parsed, dict):
                                            if parsed.get("metadata") and isinstance(parsed.get("metadata"), dict):
                                                a = parsed["metadata"].get("action")
                                                if isinstance(a, dict):
                                                    return a
                                            if parsed.get("action") and isinstance(parsed.get("action"), dict):
                                                return parsed.get("action")
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            return None

                        async for chunk in Runner.stream(starting_agent=selected_agent, input=text, context=runner_context):
                            seq += 1
                            # normalize chunk shape
                            if isinstance(chunk, dict):
                                data = chunk.get("data")
                                metadata_chunk = chunk.get("metadata")
                                chunk_seq = chunk.get("seq", seq)
                            else:
                                data = str(chunk)
                                metadata_chunk = None
                                chunk_seq = seq

                            # If runner yielded a final_output object via metadata or data, capture it
                            try:
                                if isinstance(metadata_chunk, dict) and metadata_chunk.get("stream_event_type") == "final_output":
                                    final_output = metadata_chunk.get("final_output") or data
                                elif isinstance(data, dict) and data.get("__final__"):
                                    final_output = data.get("__final__")
                            except Exception:
                                pass

                            payload = {"event": "chunk", "seq": chunk_seq, "data": data, "metadata": metadata_chunk}
                            if redis_client is not None:
                                try:
                                    safe = _make_serializable(payload)
                                    await _sh.xadd(redis_client, f"chat:{thread_id}:stream", {"data": json.dumps(safe)})
                                except Exception:
                                    logger.exception("Failed to publish chunk to chat stream")

                            logger.debug("ChatAgent: received chunk seq=%s action_detected=%s data_preview=%s", chunk_seq, None if metadata_chunk is None else metadata_chunk.get('action'), (str(data)[:200] if data is not None else None))
                            # If chunk metadata or data requested calendar.create, create job and enqueue
                            try:
                                action = _extract_action(data, metadata_chunk)
                                if action and action.get("type") == "calendar.create":
                                    try:
                                        job_service = _container.get(_container.JobServiceName)
                                        job_res = await job_service.create_calendar_job(user_id=str(user_id or "0"), name=action.get("payload", {}).get("name"), period_start=action.get("payload", {}).get("period_start"), period_end=action.get("payload", {}).get("period_end"), manifest=action.get("payload", {}).get("manifest"))
                                        # publish job-enqueued event
                                        try:
                                            if redis_client is not None:
                                                await _sh.xadd(redis_client, f"chat:{thread_id}:stream", {"data": json.dumps({"event": "calendar_job_enqueued", "job_id": str(job_res.job_id), "status": str(job_res.status)})})
                                        except Exception:
                                            logger.exception("Failed to publish calendar job enqueued event")
                                    except Exception:
                                        logger.exception("Failed to create calendar job from chunk metadata")
                                    else:
                                        logger.info("ChatAgent: enqueued calendar job job_id=%s", getattr(job_res, 'job_id', None))
                                        # expose the action as final metadata so callers receive it in the final 'done' event
                                        try:
                                            metadata = {"action": action}
                                        except Exception:
                                            pass
                            except Exception:
                                logger.exception("Error handling chunk metadata")

                        # After streaming finishes, final_output may have been captured from a final chunk
                        logger.debug("ChatAgent: streaming finished; final_output_preview=%s", (str(final_output)[:300] if final_output is not None else None))

                        # If agent produced a MealCalendarOutput (structured object) then create action
                        if MealCalendarOutput is not None and isinstance(final_output, MealCalendarOutput):
                            metadata = {"action": {"type": "calendar.create", "payload": final_output.model_dump()}}
                            reply_text = f"Generated meal calendar with {len(final_output.calendar)} days"
                        else:
                            try:
                                reply_text = str(final_output) if final_output is not None else reply_text
                                if hasattr(final_output, "model_dump") and not reply_text:
                                    reply_text = str(final_output.model_dump())
                            except Exception:
                                reply_text = reply_text

                        # publish final 'done' event to chat stream (best-effort)
                        try:
                            if redis_client is not None:
                                done_payload = {"event": "done", "seq": seq, "data": reply_text, "metadata": metadata}
                                try:
                                    safe_done = _make_serializable(done_payload)
                                    await _sh.xadd(redis_client, f"chat:{thread_id}:stream", {"data": json.dumps(safe_done)})
                                except Exception:
                                    logger.exception("Failed to publish final done event to chat stream")
                        except Exception:
                            logger.exception("Error while publishing final done event")
                    # end streaming loop
                except Exception:
                    logger.exception("Streaming Runner failed; aborting without fallback")
                    raise

        except Exception:
            # Do not silently return a legacy fallback. Surface the error so callers
            # can handle it explicitly (and so CI/tests catch misconfiguration).
            logger.exception("ChatAgent orchestration failed; aborting")
            raise

        response = {
            "thread_id": thread_id,
            "user_id": user_id,
            "reply": reply_text,
            "metadata": metadata,
        }

        # If agent returned an action to create a calendar, publish a short job-enqueued
        # event to the chat stream so frontends can react immediately. This is best-effort.
        try:
            if metadata and isinstance(metadata, dict):
                action = metadata.get("action") if isinstance(metadata.get("action"), dict) else None
                if action and action.get("type") == "calendar.create":
                    try:
                        from service import container as _container
                        from service.infrastructure.messaging import stream_helpers as _sh
                        import json

                        try:
                            redis_client = _container.get(_container.RedisClientName)
                        except Exception:
                            redis_client = None

                        if redis_client:
                            payload = {"event": "calendar_job_enqueued", "status": "enqueued", "payload": action.get("payload")}
                            # use async xadd wrapper (handles sync/async clients)
                            await _sh.xadd(redis_client, f"chat:{thread_id}:stream", {"data": json.dumps(payload)})
                    except Exception:
                        logger.exception("Failed to publish calendar_job_enqueued from ChatAgent")
        except Exception:
            # don't fail the chat flow on publish errors
            pass
        # Persist user message into session if provided
        if session is not None:
            try:
                await session.add_items([
                    {"role": "user", "content": text, "ts": datetime.now(timezone.utc).isoformat()},
                ])
                # persist assistant reply as well for conversation history
                try:
                    await session.add_items([
                        {"role": "assistant", "content": reply_text, "ts": datetime.now(timezone.utc).isoformat()},
                    ])
                except Exception:
                    logger.exception("Failed to add assistant reply to session")
            except Exception:
                logger.exception("Failed to add user message to session")

        return response
