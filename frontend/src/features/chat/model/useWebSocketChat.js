import { useState, useEffect, useRef, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
const HEARTBEAT_TIMEOUT_MS = 30000;
const HEARTBEAT_CHECK_INTERVAL_MS = 10000;

function buildWsUrl(threadId, lastId) {
  const rawBase =
    import.meta.env?.VITE_WS_BASE_URL ||
    import.meta.env?.VITE_API_BASE_URL ||
    '';

  let base = rawBase.trim().replace(/\/$/, '');
  if (!base) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    base = `${proto}//${window.location.host}`;
  } else if (base.startsWith('http://')) {
    base = `ws://${base.slice(7)}`;
  } else if (base.startsWith('https://')) {
    base = `wss://${base.slice(8)}`;
  }

  const params = lastId ? `?last_id=${encodeURIComponent(lastId)}` : '';
  return `${base}/api/chats/${threadId}/ws${params}`;
}

export function useWebSocketChat(threadId, callbacks = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [currentJob, setCurrentJob] = useState(null);
  const [connectionState, setConnectionState] = useState('disconnected');
  const [lastHeartbeat, setLastHeartbeat] = useState(null);
  const [streamingMessage, setStreamingMessage] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY_MS);
  const connectingRef = useRef(false);
  const prevThreadIdRef = useRef(null);
  const messageQueueRef = useRef([]);
  const lastIdRef = useRef(null);
  const heartbeatCheckRef = useRef(null);
  const connectRef = useRef(null);

  const toast = useToast();

  const {
    onMessage,
    onJobCreated,
    onComplete,
    onError,
    onConnect,
    onDisconnect,
    onAgentReply,
    onStreamChunk,
  } = callbacks;

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      toast({ title: 'Соединение потеряно', description: 'Не удалось восстановить соединение с чатом.', status: 'warning', duration: 10000 });
      return;
    }
    reconnectAttemptsRef.current += 1;
    const delay = reconnectDelayRef.current;
    reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY_MS);
    reconnectTimeoutRef.current = setTimeout(() => connectRef.current?.(), delay);
  }, [toast]);

  const handleIncomingMessage = useCallback((data) => {
    const eventType = data.type || data.event;

    switch (eventType) {
      case 'replay':
      case 'claimed': {
        // Deliver replayed/claimed stream entries as messages
        const inner = data.data || {};
        const innerType = inner.type || inner.event;
        if (innerType) {
          handleIncomingMessage({ ...inner });
        }
        break;
      }

      case 'heartbeat':
        setLastHeartbeat(Date.now());
        break;

      case 'job_created': {
        const job = {
          id: data.job_id,
          celeryTaskId: data.celery_task_id || null,
          status: 'processing',
        };
        setCurrentJob(job);
        onJobCreated?.(data);
        break;
      }

      case 'stream_chunk':
        setStreamingMessage((prev) => {
          if (!prev) {
            const newMsg = {
              id: `stream_${Date.now()}_${Math.random()}`,
              type: 'agent',
              content: data.data || '',
              timestamp: new Date().toISOString(),
              isStreaming: true,
            };
            setMessages((msgs) => [...msgs, newMsg]);
            return newMsg;
          }
          const updated = { ...prev, content: prev.content + (data.data || '') };
          setMessages((msgs) => msgs.map((m) => (m.id === prev.id ? updated : m)));
          return updated;
        });
        onStreamChunk?.(data);
        break;

      case 'agent_reply': {
        setStreamingMessage((prev) => {
          if (prev) {
            setMessages((msgs) =>
              msgs.map((m) => (m.id === prev.id ? { ...m, content: data.reply ?? m.content, complete: true, isStreaming: false } : m))
            );
            return null;
          }
          const msg = {
            id: `agent_${Date.now()}_${Math.random()}`,
            type: 'agent',
            content: data.reply || '',
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata || null,
            file_url: data.file_url || null,
            complete: true,
            isStreaming: false,
          };
          setMessages((msgs) => [...msgs, msg]);
          onMessage?.(msg);
          return null;
        });
        onAgentReply?.(data);
        break;
      }

      case 'agent_complete':
        setCurrentJob(null);
        onComplete?.(data);
        break;

      case 'error': {
        const errorText = data.error || data?.data?.message || 'Неизвестная ошибка';
        setCurrentJob(null);
        setStreamingMessage(null);
        onError?.(new Error(errorText));
        toast({ title: 'Ошибка', description: errorText, status: 'error', duration: 5000 });
        break;
      }

      default:
        break;
    }
  }, [onMessage, onJobCreated, onComplete, onError, onAgentReply, onStreamChunk, toast]);

  const connect = useCallback(() => {
    if (connectingRef.current || !threadId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;

    connectingRef.current = true;
    setConnectionState('connecting');

    setTimeout(() => {
      if (!connectingRef.current) return;
      let wsUrl;
      try {
        wsUrl = buildWsUrl(threadId, lastIdRef.current);
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          setConnectionState('connected');
          reconnectAttemptsRef.current = 0;
          reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
          connectingRef.current = false;
          onConnect?.(threadId);
          messageQueueRef.current.forEach((msg) => {
            try { ws.send(JSON.stringify(msg)); } catch (_) {}
          });
          messageQueueRef.current = [];
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.id) lastIdRef.current = data.id;
            handleIncomingMessage(data);
          } catch (err) {
            onError?.(err);
          }
        };

        ws.onclose = (event) => {
          setIsConnected(false);
          setConnectionState('disconnected');
          setLastHeartbeat(null);
          connectingRef.current = false;
          if (heartbeatCheckRef.current) {
            clearInterval(heartbeatCheckRef.current);
            heartbeatCheckRef.current = null;
          }
          onDisconnect?.(event);
          if (event.code !== 1000 && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
            scheduleReconnect();
          }
        };

        ws.onerror = () => {
          setConnectionState('error');
          connectingRef.current = false;
          onError?.(new Error('WebSocket connection error'));
        };
      } catch (err) {
        setConnectionState('error');
        connectingRef.current = false;
        onError?.(err);
      }
    }, 50);
  }, [threadId, handleIncomingMessage, onConnect, onDisconnect, onError, scheduleReconnect]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const sendMessage = useCallback((text, selectedModel = null, inputType = null, options = {}) => {
    if (!text?.trim()) return;

    const userMsg = {
      id: `msg_${Date.now()}_${Math.random()}`,
      type: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    const payload = {
      type: 'message',
      text: text.trim(),
      id: userMsg.id,
      timestamp: userMsg.timestamp,
      ...(selectedModel && { model: selectedModel }),
      ...(inputType && { input_type: inputType }),
      ...(options.webSearch && { web_search: true }),
      ...(options.deepResearch && { deep_research: true }),
      ...(options.fileContext && { file_context: options.fileContext }),
      ...(Array.isArray(options.fileIds) && options.fileIds.length && { file_ids: options.fileIds }),
      ...(options.routeOverride && { route_override: options.routeOverride }),
    };

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try { wsRef.current.send(JSON.stringify(payload)); }
      catch (err) { messageQueueRef.current.push(payload); onError?.(err); }
    } else {
      messageQueueRef.current.push(payload);
    }
  }, [onError]);

  const cancelJob = useCallback(async (jobId) => {
    const targetTaskId = currentJob?.celeryTaskId;
    if (targetTaskId) {
      const { cancelTask } = await import('@api/jobs');
      await cancelTask(targetTaskId);
    }
    setCurrentJob((prev) => (prev ? { ...prev, status: 'cancelled' } : prev));
  }, [currentJob]);

  const reconnect = useCallback(() => {
    wsRef.current?.close(1000, 'Manual reconnect');
    setTimeout(() => connect(), 100);
  }, [connect]);

  // Auto-connect and cleanup when threadId changes
  useEffect(() => {
    const threadChanged = prevThreadIdRef.current !== threadId;
    if (threadId && threadChanged) {
      messageQueueRef.current = [];
      connectingRef.current = false;
      setConnectionState('disconnected');
      setIsConnected(false);
      connectRef.current?.();
    }
    prevThreadIdRef.current = threadId;

    return () => {
      wsRef.current?.close(1000, 'Thread ID changed');
      wsRef.current = null;
      connectingRef.current = false;
      setConnectionState('disconnected');
      setIsConnected(false);
      setLastHeartbeat(null);
      setStreamingMessage(null);
    };
  }, [threadId]);

  // Heartbeat monitoring
  useEffect(() => {
    if (connectionState !== 'connected' || !lastHeartbeat) return;
    heartbeatCheckRef.current = setInterval(() => {
      if (Date.now() - lastHeartbeat > HEARTBEAT_TIMEOUT_MS) {
        setConnectionState('error');
        scheduleReconnect();
      }
    }, HEARTBEAT_CHECK_INTERVAL_MS);
    return () => {
      clearInterval(heartbeatCheckRef.current);
      heartbeatCheckRef.current = null;
    };
  }, [connectionState, lastHeartbeat, scheduleReconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close(1000, 'Component unmount');
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (heartbeatCheckRef.current) clearInterval(heartbeatCheckRef.current);
      connectingRef.current = false;
    };
  }, []);

  return {
    isConnected,
    connectionState,
    messages,
    currentJob,
    streamingMessage,
    reconnectAttempts: reconnectAttemptsRef.current,
    sendMessage,
    cancelJob,
    reconnect,
    clearMessages: () => setMessages([]),
    getConnectionInfo: () => ({
      state: connectionState,
      attempts: reconnectAttemptsRef.current,
      url: wsRef.current?.url || null,
      lastHeartbeat: lastHeartbeat ? new Date(lastHeartbeat).toISOString() : null,
    }),
  };
}
