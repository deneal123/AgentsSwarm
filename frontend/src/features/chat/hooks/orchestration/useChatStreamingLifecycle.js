import { useCallback, useEffect, useMemo, useRef } from 'react';
import { clampTraceDetail } from '../../utils/trace';

export function useChatStreamingLifecycle({ isLoading, setIsLoading, setError, appendTraceEvent, finalizeTraceSession, setMessages, setInputValue }) {
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
    setIsLoading(true);
  }, [resolveWsEventJobId, setIsLoading]);

  const onComplete = useCallback(() => setIsLoading(false), [setIsLoading]);

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
    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (lastMessage && lastMessage.type === 'agent' && !lastMessage.complete) {
        const chunkedContent = `${lastMessage.content}${data.data}`;
        return prev.map((msg, index) => (index === prev.length - 1 ? { ...msg, content: chunkedContent, typingProgress: Math.min(1, chunkedContent.length / 1000), metadata: { ...(msg.metadata || {}), ...chunkMeta } } : msg));
      }
      return [...prev, { id: `agent_${Date.now()}_${Math.random()}`, type: 'agent', content: data.data, timestamp: new Date().toISOString(), metadata: chunkMeta, complete: false, isTyping: true, typingProgress: 0 }];
    });
  }, [setMessages, shouldIgnoreWsEvent]);

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
    setMessages((prev) => [...prev, { id: `agent_${Date.now()}_${Math.random()}`, type: 'agent', content: incomingReply, timestamp: new Date().toISOString(), metadata: data.metadata, file_url: data.file_url, complete: true, isTyping: false, typingProgress: 1 }]);
    setIsLoading(false);
    setInputValue('');
    finalizeTraceSession(data?.metadata?.provider_unavailable ? 'error' : 'done');
  }, [appendTraceEvent, finalizeTraceSession, resolveWsEventJobId, setInputValue, setIsLoading, setMessages, shouldIgnoreWsEvent]);

  const onAgentComplete = useCallback((data) => {
    if (shouldIgnoreWsEvent(data)) return;
    setMessages((prev) => prev.map((msg, index) => (index === prev.length - 1 && msg.type === 'agent' && msg.isTyping ? { ...msg, isTyping: false, complete: true, typingProgress: 1 } : msg)));
  }, [setMessages, shouldIgnoreWsEvent]);

  const onAgentEvent = useCallback((event) => {
    if (!event?.type || shouldIgnoreWsEvent(event)) return;
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
  }, [appendTraceEvent, shouldIgnoreWsEvent]);

  const wsCallbacks = useMemo(() => ({ onMessage: () => {}, onJobCreated, onComplete, onError, onStreamChunk, onAgentReply, onAgentComplete, onAgentEvent }), [onAgentComplete, onAgentEvent, onAgentReply, onComplete, onError, onJobCreated, onStreamChunk]);

  return { state: {}, actions: { wsCallbacks } };
}
