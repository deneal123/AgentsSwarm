import { useCallback, useEffect, useMemo, useRef } from 'react';
import { clampTraceDetail } from '../../utils/trace';

export function useChatStreamingLifecycle({ isLoading, setIsLoading, setError, appendTraceEvent, finalizeTraceSession, addMessage, appendStreamChunk, completeLastAgentMessage, finalizeStreamWithContent, setCurrentJob, clearCurrentJob, setInputValue, onOrchestratorEvent }) {
  const isLoadingRef = useRef(false);
  const activeWsJobIdRef = useRef('');
  const lastWsReplyFingerprintRef = useRef('');

  useEffect(() => {
    isLoadingRef.current = isLoading;
  }, [isLoading]);

  const resolveWsEventJobId = useCallback((payload) => String(payload?.job_id || payload?.metadata?.job_id || '').trim(), []);

  const shouldIgnoreWsEvent = useCallback((payload) => {
    const incomingJobId = resolveWsEventJobId(payload);
    if (!incomingJobId) return false;
    const activeJobId = String(activeWsJobIdRef.current || '').trim();
    if (!activeJobId) {
      activeWsJobIdRef.current = incomingJobId;
      return false;
    }
    return activeJobId !== incomingJobId;
  }, [resolveWsEventJobId]);

  const onJobCreated = useCallback((data) => {
    const incomingJobId = resolveWsEventJobId(data);
    if (incomingJobId) {
      activeWsJobIdRef.current = incomingJobId;
      lastWsReplyFingerprintRef.current = '';
    }
    setCurrentJob(incomingJobId ? { id: incomingJobId, status: 'processing', progress: 0 } : null);
    setIsLoading(true);
  }, [resolveWsEventJobId, setCurrentJob, setIsLoading]);

  const onComplete = useCallback(() => { clearCurrentJob(); setIsLoading(false); }, [clearCurrentJob, setIsLoading]);

  const onError = useCallback((err) => {
    const rawMessage = String(err?.message || '').trim();
    appendTraceEvent({ kind: 'error', title: 'Ошибка канала обработки', detail: rawMessage || 'Ошибка соединения с чатом' });
    if (/403|401|permission|forbidden|unauthorized/i.test(rawMessage)) {
      finalizeTraceSession('error');
      setError('Модель недоступна для текущего ключа API. Попробуйте другой профиль/модель.');
      setIsLoading(false);
      return;
    }
    finalizeTraceSession('error');
    setError(rawMessage ? `Ошибка чата: ${rawMessage}` : 'Ошибка соединения с чатом. Переключились на резервный режим.');
    setIsLoading(false);
  }, [appendTraceEvent, finalizeTraceSession, setError, setIsLoading]);

  const onStreamChunk = useCallback((data) => {
    if (!isLoadingRef.current || shouldIgnoreWsEvent(data) || !data?.data?.trim()) return;
    const chunkMeta = data.metadata || {};
    appendStreamChunk(data.data, chunkMeta);
  }, [appendStreamChunk, shouldIgnoreWsEvent]);

  const onAgentReply = useCallback((data) => {
    if (shouldIgnoreWsEvent(data)) return;
    if (!data.reply || !data.reply.trim()) {
      finalizeTraceSession('error');
      setIsLoading(false);
      return;
    }
    const incomingReply = data.reply.trim();
    const incomingJobId = resolveWsEventJobId(data) || String(activeWsJobIdRef.current || '').trim() || 'unknown_job';
    const replyFingerprint = `${incomingJobId}::${incomingReply}`;
    if (lastWsReplyFingerprintRef.current === replyFingerprint) {
      setIsLoading(false);
      return;
    }
    lastWsReplyFingerprintRef.current = replyFingerprint;
    appendTraceEvent({ kind: data?.metadata?.provider_unavailable ? 'error' : 'done', title: data?.metadata?.provider_unavailable ? 'Ответ сформирован в деградированном режиме' : 'Ответ сформирован', detail: data?.metadata?.provider_error || '' });
    // Finalize the streaming message with authoritative final content rather than adding a second bubble.
    // Falls back to addMessage if no streaming message exists (e.g. chunk-less path).
    if (finalizeStreamWithContent) {
      finalizeStreamWithContent(incomingReply, data.metadata, data.file_url);
    } else {
      addMessage({ id: `agent_${Date.now()}_${Math.random()}`, type: 'agent', content: incomingReply, timestamp: new Date().toISOString(), metadata: data.metadata, file_url: data.file_url, complete: true, isTyping: false, typingProgress: 1 });
    }
    setIsLoading(false);
    setInputValue('');
    finalizeTraceSession(data?.metadata?.provider_unavailable ? 'error' : 'done');
  }, [addMessage, appendTraceEvent, finalizeStreamWithContent, finalizeTraceSession, resolveWsEventJobId, setInputValue, setIsLoading, shouldIgnoreWsEvent]);

  const onAgentComplete = useCallback((data) => {
    if (shouldIgnoreWsEvent(data)) return;
    completeLastAgentMessage();
  }, [completeLastAgentMessage, shouldIgnoreWsEvent]);

  const onAgentEvent = useCallback((event) => {
    if (!event?.type || shouldIgnoreWsEvent(event)) return;

    // Dispatch orchestrator-specific events to orchestrator state manager
    if (event.type === 'status_update' && event.metadata?.event_type?.startsWith('orchestrator_')) {
      onOrchestratorEvent?.(event);
      // Also show a trace entry for key milestones
      const orchEventType = event.metadata.event_type;
      if (orchEventType === 'orchestrator_task_created') {
        appendTraceEvent({ kind: 'done', title: `Задача роя создана: ${event.metadata.task_id || ''}`, detail: 'Оркестратор принял задачу, начинается выполнение', timestamp: event.timestamp });
      } else if (orchEventType === 'orchestrator_synthesizing') {
        appendTraceEvent({ kind: 'info', title: 'Формирую инструкцию для роя роботов', detail: 'Анализирую многомодальный контекст', timestamp: event.timestamp });
      }
      return;
    }

    // structured_output with orchestrator images → dispatch to orchestrator state
    if (event.type === 'structured_output' && event.metadata?.event_type === 'orchestrator_images') {
      onOrchestratorEvent?.(event);
      return;
    }

    if (event.type === 'tool_call_complete') {
      appendTraceEvent({ kind: 'done', title: `Инструмент завершен: ${event.tool_name || 'external_tool'}`, detail: clampTraceDetail(event.result), timestamp: event.timestamp });
      return;
    }
    const mapping = {
      routing_start: { kind: 'info', title: 'Маршрутизатор анализирует запрос', detail: event.message || 'Подбор оптимального агента и модели' },
      routing_complete: { kind: 'done', title: `Выбран агент: ${event.agent_name || 'auto'}`, detail: event.message || '' },
      agent_start: { kind: 'done', title: `Запущен агент: ${event.agent_name || 'assistant'}`, detail: event.message || 'Начата генерация ответа' },
      tool_call_start: { kind: 'info', title: `Вызван инструмент: ${event.tool_name || 'external_tool'}`, detail: event.agent_name ? `Инициатор: ${event.agent_name}` : '' },
      structured_output: { kind: 'done', title: 'Подготовлен структурированный результат', detail: 'Данные готовы для отображения в UI' },
      error: { kind: 'error', title: 'Ошибка во время обработки', detail: event.error || 'Неизвестная ошибка' },
    };
    if (mapping[event.type]) appendTraceEvent({ ...mapping[event.type], timestamp: event.timestamp });
  }, [appendTraceEvent, onOrchestratorEvent, shouldIgnoreWsEvent]);

  const wsCallbacks = useMemo(() => ({ onMessage: () => {}, onJobCreated, onComplete, onError, onStreamChunk, onAgentReply, onAgentComplete, onAgentEvent }), [onAgentComplete, onAgentEvent, onAgentReply, onComplete, onError, onJobCreated, onStreamChunk, onOrchestratorEvent]);

  return { state: {}, actions: { wsCallbacks } };
}
