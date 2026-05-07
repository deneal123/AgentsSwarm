import { useCallback, useRef } from 'react';

export function useChatStreamingLifecycle({ setIsLoading, setError, appendTraceEvent, finalizeTraceSession, setMessages, setInputValue }) {
  const activeWsJobIdRef = useRef('');

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
    if (incomingJobId) activeWsJobIdRef.current = incomingJobId;
    setIsLoading(true);
  }, [resolveWsEventJobId, setIsLoading]);

  const onStreamChunk = useCallback((data) => {
    if (shouldIgnoreWsEvent(data) || !data?.data?.trim()) return;
    setMessages((prev) => ([...prev, { id: `agent_${Date.now()}`, type: 'agent', content: data.data, complete: false, isTyping: true }]));
  }, [setMessages, shouldIgnoreWsEvent]);

  const onComplete = useCallback(() => setIsLoading(false), [setIsLoading]);

  const onError = useCallback((err) => {
    const message = String(err?.message || '').trim() || 'Ошибка соединения с чатом';
    appendTraceEvent({ kind: 'error', title: 'Ошибка канала обработки', detail: message });
    finalizeTraceSession('error');
    setError(message);
    setIsLoading(false);
  }, [appendTraceEvent, finalizeTraceSession, setError, setIsLoading]);

  const onAgentReply = useCallback((data) => {
    if (shouldIgnoreWsEvent(data) || !data?.reply?.trim()) return;
    setMessages((prev) => ([...prev, { id: `agent_${Date.now()}`, type: 'agent', content: data.reply.trim(), complete: true, isTyping: false }]));
    setInputValue('');
    finalizeTraceSession('done');
    setIsLoading(false);
  }, [finalizeTraceSession, setInputValue, setIsLoading, setMessages, shouldIgnoreWsEvent]);

  return {
    state: {},
    actions: { onJobCreated, onStreamChunk, onComplete, onError, onAgentReply, shouldIgnoreWsEvent },
  };
}
