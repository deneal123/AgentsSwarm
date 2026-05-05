import { useState, useEffect, useRef, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';

/**
 * useWebSocketChat - Хук для работы с WebSocket соединением чат-агентов
 *
 * Управляет:
 * - Подключением к WebSocket
 * - Обработкой входящих сообщений
 * - Автореконнектом при разрыве
 * - Состоянием соединения
 *
 * @param {string} threadId - ID чат-треда
 * @param {Object} callbacks - Колбеки для обработки событий
 * @param {boolean} isAuthenticated - Флаг авторизации пользователя
 * @returns {Object} WebSocket состояние и методы
 */
export function useWebSocketChat(threadId, callbacks = {}, isAuthenticated = false) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [currentJob, setCurrentJob] = useState(null);
  const [connectionState, setConnectionState] = useState('disconnected'); // 'connecting', 'connected', 'disconnected', 'error'
  const [lastHeartbeat, setLastHeartbeat] = useState(null);
  const heartbeatCheckRef = useRef(null);

  // Agent status tracking for dynamic hints
  const [agentStatus, setAgentStatus] = useState(null); // { type: 'routing'|'tool_call'|'processing', message: string, agent_name?: string }
  const [agentTimeline, setAgentTimeline] = useState([]); // Persistent execution steps for UI
  const [streamingMessage, setStreamingMessage] = useState(null); // Current streaming message being built

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const connectRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = useRef(1000); // Начальная задержка 1с
  const connectingRef = useRef(false); // Флаг для предотвращения множественных подключений
  const prevThreadIdRef = useRef(null); // Для отслеживания изменения threadId

  const toast = useToast();

  const {
    onMessage,
    onJobUpdate,
    onJobCreated,
    onComplete,
    onError,
    onConnect,
    onDisconnect,
    onJobProgress,
    onAgentComplete,
    onAgentEvent,
  } = callbacks;

  const appendAgentTimeline = useCallback((step) => {
    if (!step?.message) return;
    const enrichedStep = {
      id: `step_${Date.now()}_${Math.random()}`,
      timestamp: new Date().toISOString(),
      ...step,
    };
    setAgentTimeline(prev => [...prev.slice(-29), enrichedStep]);
  }, []);

  const formatAgentName = useCallback((agentName) => {
    const name = String(agentName || '').trim();
    const map = {
      deep_research: 'Глубокий ресерч',
      web_search: 'Веб-поиск',
      audio_transcribe: 'Распознавание аудио',
      image_gen: 'Генерация изображений',
      pptx_gen: 'Генерация презентации',
      general: 'Универсальный агент',
    };
    return map[name] || name || 'Агент';
  }, []);

  const localizeHumanText = useCallback((rawText) => {
    const text = String(rawText || '').trim();
    if (!text) return text;

    const exact = {
      'Determining appropriate agent...': 'Определяю подходящего агента...',
      'Searching the web...': 'Выполняю поиск в интернете...',
      'Starting deep research': 'Запускаю глубокий ресерч',
      'Starting web search': 'Запускаю веб-поиск',
      'Starting image generation': 'Запускаю генерацию изображения',
      'Deep research completed': 'Глубокий ресерч завершён',
      'Web search completed': 'Веб-поиск завершён',
      'Image generation completed': 'Генерация изображения завершена',
      'Recipe request needs reasoning and a capable language model.': 'Запрос требует усиленного рассуждения и подходящей языковой модели.',
      'Sensitive topic, requires strong reasoning and safety guardrails.': 'Чувствительная тема: применены усиленные рассуждения и защитные ограничения.',
      'Explicit request to generate an image; use image model.': 'Явный запрос на генерацию изображения — использую image-модель.',
    };
    if (exact[text]) return exact[text];

    let out = text;
    out = out.replace(
      /^Explicit request to generate an image(?:\s+of\s+(.+?))?\.?$/i,
      (_m, subject) => subject
        ? `Явный запрос на генерацию изображения (${subject.trim()}).`
        : 'Явный запрос на генерацию изображения.'
    );
    out = out.replace(/^Routed to\s+/i, 'Выбран агент: ');
    out = out.replace(/^Found\s+(\d+)\s+results$/i, 'Найдено результатов: $1');
    out = out.replace(/safety guardrails/gi, 'защитные ограничения');
    out = out.replace(/guardrails/gi, 'защитные ограничения');
    return out;
  }, []);

  const extractReasoningMessage = useCallback((payload) => {
    const candidate = payload?.reasoning
      || payload?.reason
      || payload?.thinking
      || payload?.metadata?.reasoning
      || payload?.metadata?.reason
      || payload?.metadata?.model_routing?.reason;
    if (!candidate) return null;
    const localized = localizeHumanText(candidate);
    return String(localized).trim() || null;
  }, [localizeHumanText]);

  const normalizeWsBaseUrl = useCallback((rawBaseUrl) => {
    if (!rawBaseUrl) {
      return null;
    }

    const trimmed = String(rawBaseUrl).trim().replace(/\/$/, '');
    if (!trimmed) {
      return null;
    }

    if (trimmed.startsWith('ws://') || trimmed.startsWith('wss://')) {
      return trimmed;
    }

    if (trimmed.startsWith('http://')) {
      return `ws://${trimmed.slice('http://'.length)}`;
    }

    if (trimmed.startsWith('https://')) {
      return `wss://${trimmed.slice('https://'.length)}`;
    }

    return trimmed;
  }, []);

  // Получение WebSocket URL с токеном аутентификации
  const getWebSocketUrl = useCallback((threadId) => {
    // Use WebSocket base URL from env or API base URL
    const wsBaseUrl = (import.meta.env?.REACT_APP_WS_BASE_URL || import.meta.env?.REACT_APP_API_BASE_URL) ||
                     (process.env?.REACT_APP_WS_BASE_URL || process.env?.REACT_APP_API_BASE_URL);


    let baseUrlStr = normalizeWsBaseUrl(wsBaseUrl);
    if (!baseUrlStr) {
      const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (isLocalHost) {
        baseUrlStr = 'ws://localhost:8000';
      } else {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        baseUrlStr = `${protocol}//${window.location.host}`;
      }
    }

    // Token strategy:
    // - authenticated: prefer legacy session token if present; otherwise rely on HttpOnly auth_token cookie
    //   automatically sent by browser during WS handshake
    // - anonymous: explicit anon token
    let token;
    if (isAuthenticated) {
      token = document.cookie
        .split('; ')
        .find(row => row.startsWith('session_token='))
        ?.split('=')[1] ||
        document.cookie
          .split('; ')
          .find(row => row.startsWith('session='))
          ?.split('=')[1] ||
        '';
    } else {
      token = 'anon-token';
    }

    const timestamp = Date.now();
    const tokenQuery = token ? `token=${encodeURIComponent(token)}&` : '';
    const wsUrl = `${baseUrlStr}/api/chats/${threadId}/ws?${tokenQuery}t=${timestamp}`;
    return wsUrl;
  }, [isAuthenticated, normalizeWsBaseUrl]);

  // Обработка входящих сообщений
  const handleIncomingMessage = useCallback((data) => {
    try {
      const switchValue = data.type || data.event;

      const emitAgentEvent = (type, payload = {}) => {
        if (onAgentEvent) {
          onAgentEvent({
            type,
            timestamp: new Date().toISOString(),
            ...payload,
          });
        }
      };

      // Обработка разных типов сообщений
      switch (switchValue) {
      case 'job_created':
        // Создание фоновой задачи
        const job = {
          id: data.job_id,
          celeryTaskId: data.celery_task_id,
          status: 'processing',
          progress: 0,
          type: data.type || 'unknown'
        };
        setCurrentJob(job);

        if (onJobUpdate) onJobUpdate(data);
        if (onJobCreated) onJobCreated(data);
        break;

      case 'processing':
        // Агент начал обработку
        setCurrentJob(prev => prev ? {
          ...prev,
          status: 'processing',
          progress: 10
        } : null);

        if (onJobProgress) onJobProgress({ job_id: data.job_id, status: 'processing', progress: 10 });
        break;

      case 'calendar_generating':
        // Генерация календаря
        setCurrentJob(prev => prev ? {
          ...prev,
          status: 'generating_calendar',
          progress: 50
        } : null);

        if (onJobProgress) onJobProgress({ job_id: data.job_id, status: 'generating_calendar', progress: 50 });
        break;

      case 'calendar_generated':
        // Календарь готов
        setCurrentJob(prev => prev ? {
          ...prev,
          status: 'calendar_ready',
          progress: 80,
          fileUrl: data.file_url
        } : null);
        setMessages(prev => prev.map(msg =>
          msg.id.startsWith('agent_') && msg.type === 'agent'
            ? { ...msg, fileUrl: data.file_url }
            : msg
        ));

        if (onJobProgress) onJobProgress({
          job_id: data.job_id,
          status: 'calendar_ready',
          progress: 80,
          file_url: data.file_url
        });
        break;


      case 'agent_response':
        // Чанк ответа агента (legacy support)
        const chunkMessage = {
          id: `msg_${Date.now()}_${Math.random()}`,
          type: 'agent',
          content: data.data || '',
          timestamp: new Date().toISOString(),
          chunk: true,
          seq: data.seq
        };
        setMessages(prev => [...prev, chunkMessage]);
        if (onMessage) onMessage(chunkMessage);
        break;

      case 'job_progress':
        // Обновление прогресса задачи (legacy support)
        setCurrentJob(prev => prev ? {
          ...prev,
          progress: data.progress || 0,
          status: data.status || prev.status
        } : null);

        if (onJobProgress) onJobProgress(data);
        break;

      case 'heartbeat':
        // Heartbeat - обновляем время последнего heartbeat
        const now = Date.now();
        setLastHeartbeat(now);
        break;

      case 'routing_start':
        // Начало маршрутизации
        emitAgentEvent('routing_start', {
          message: data.message,
          job_id: data.job_id,
        });
        {
          const routingMsg = localizeHumanText(data.message) || 'Определяю подходящего агента...';
          setAgentStatus({
            type: 'routing',
            message: routingMsg,
            agent_name: null
          });
          const reasoning = extractReasoningMessage(data);
          appendAgentTimeline({ type: 'routing_start', message: `🧭 ${routingMsg}`, reasoning });
        }
        break;

      case 'routing_complete':
        // Маршрутизация завершена
        emitAgentEvent('routing_complete', {
          message: data.message,
          agent_name: data.agent_name,
          job_id: data.job_id,
        });
        {
          const agentLabel = formatAgentName(data.agent_name);
          setAgentStatus({
            type: 'routing_complete',
            message: `Выбран агент: ${agentLabel}`,
            agent_name: data.agent_name
          });
          const reasoning = extractReasoningMessage(data);
          appendAgentTimeline({
            type: 'routing_complete',
            message: `✅ Выбран агент: ${agentLabel}`,
            agent_name: data.agent_name,
            reasoning,
          });
        }
        // Clear routing status after a short delay
        setTimeout(() => setAgentStatus(null), 2000);
        break;

      case 'agent_start':
        // Агент начал обработку
        emitAgentEvent('agent_start', {
          message: data.message,
          agent_name: data.agent_name,
          job_id: data.job_id,
        });
        {
          const agentLabel = formatAgentName(data.agent_name);
          setAgentStatus({
            type: 'processing',
            message: `${agentLabel} начинает обработку...`,
            agent_name: data.agent_name
          });
          appendAgentTimeline({
            type: 'agent_start',
            message: `🤖 ${agentLabel} начинает обработку...`,
            agent_name: data.agent_name,
          });
        }
        break;

      case 'agent_complete':
        // Агент завершил обработку
        emitAgentEvent('agent_complete', {
          agent_name: data.agent_name,
          job_id: data.job_id,
        });
        setAgentStatus(null);
        setCurrentJob(null);
        if (data.reply) {
          const finalMessage = {
            id: `msg_${Date.now()}_${Math.random()}`,
            type: 'agent',
            content: data.reply,
            timestamp: new Date().toISOString(),
            metadata: data.metadata,
            fileUrl: data.file_url,
            complete: true,
          };
          setMessages(prev => [...prev, finalMessage]);
        }
        appendAgentTimeline({
          type: 'agent_complete',
          message: `✅ ${formatAgentName(data.agent_name)} завершил работу`,
          agent_name: data.agent_name,
        });
        if (onComplete) onComplete(data);
        if (onAgentComplete) {
          onAgentComplete(data);
        }
        break;

      case 'tool_call_start':
        // Начало использования инструмента
        emitAgentEvent('tool_call_start', {
          tool_name: data.tool_name,
          agent_name: data.agent_name,
          job_id: data.job_id,
        });
        setAgentStatus({
          type: 'tool_call',
          message: `Агент использует инструмент: ${data.tool_name}`,
          agent_name: data.agent_name,
          tool_name: data.tool_name
        });
        appendAgentTimeline({
          type: 'tool_call_start',
          message: `🔧 Инструмент: ${data.tool_name}`,
          agent_name: data.agent_name,
          tool_name: data.tool_name,
        });
        break;

      case 'tool_call_complete':
        // Завершение использования инструмента
        emitAgentEvent('tool_call_complete', {
          tool_name: data.tool_name,
          result: data.result,
          agent_name: data.agent_name,
          job_id: data.job_id,
        });
        setAgentStatus({
          type: 'tool_complete',
          message: `Завершено использование инструмента: ${data.tool_name}`,
          agent_name: data.agent_name,
          tool_name: data.tool_name
        });
        appendAgentTimeline({
          type: 'tool_call_complete',
          message: `✅ Инструмент завершён: ${data.tool_name}`,
          agent_name: data.agent_name,
          tool_name: data.tool_name,
        });
        // Clear tool status after a short delay
        setTimeout(() => setAgentStatus(null), 1500);
        break;

      case 'stream_chunk':
        // Получен чанк стриминга от агента

        // Initialize streaming message if not exists
        setStreamingMessage(prev => {
          if (!prev) {
            const newMessage = {
              id: `stream_${Date.now()}_${Math.random()}`,
              type: 'agent',
              content: data.data || '',
              timestamp: new Date().toISOString(),
              isStreaming: true,
              complete: false
            };
            // Add to messages if it's the first chunk
            setMessages(prevMessages => [...prevMessages, newMessage]);
            return newMessage;
          } else {
            // Update existing streaming message
            const updatedMessage = {
              ...prev,
              content: prev.content + (data.data || '')
            };
            setMessages(prevMessages =>
              prevMessages.map(msg =>
                msg.id === prev.id ? updatedMessage : msg
              )
            );
            return updatedMessage;
          }
        });

        callbacks.onStreamChunk?.(data);
        break;

      case 'stream_complete':
        // Поток завершён: гарантированно сбрасываем индикаторы обработки
        setCurrentJob(null);
        setAgentStatus(null);
        if (onComplete) onComplete(data);
        break;

      case 'agent_reply':
        // Получен полный ответ от агента

        // If we were streaming, mark as complete
        if (streamingMessage) {
          setMessages(prevMessages =>
            prevMessages.map(msg =>
              msg.id === streamingMessage.id
                ? { ...msg, complete: true, isStreaming: false }
                : msg
            )
          );
          setStreamingMessage(null);
        } else {
          // Fallback: create complete message
          const agentMessage = {
            id: `agent_${Date.now()}_${Math.random()}`,
            type: 'agent',
            content: data.reply,
            timestamp: new Date().toISOString(),
            metadata: data.metadata,
            file_url: data.file_url,
            complete: true,
            isStreaming: false
          };
          setMessages(prev => [...prev, agentMessage]);
        }

        callbacks.onAgentReply?.(data);
        setCurrentJob(null); // Сбрасываем текущий job
        setAgentStatus(null); // Clear any remaining status
        break;

      case 'structured_output':
        // Структурированный вывод (например, календарь)
        emitAgentEvent('structured_output', {
          data: data.data,
          job_id: data.job_id,
        });
        setAgentStatus({
          type: 'structured_output',
          message: 'Обрабатываю структурированные данные...',
          data: data.data
        });
        // Clear after processing
        setTimeout(() => setAgentStatus(null), 2000);
        break;

      case 'error':
        // Ошибка обработки
        console.error('❌ Error from server:', data.error);
        emitAgentEvent('error', {
          error: data.error,
          job_id: data.job_id,
        });
        setCurrentJob(null);
        if (onError) onError(new Error(data.error || 'Unknown websocket error'));
        appendAgentTimeline({
          type: 'error',
          message: `❌ Ошибка: ${data.error || 'неизвестная ошибка'}`,
        });
        // Показываем ошибку пользователю
        toast({
          title: 'Ошибка',
          description: data.error || 'Произошла ошибка при обработке сообщения',
          status: 'error',
          duration: 5000,
        });
        break;

      default:
    }
    } catch (error) {
      console.error('Error processing WebSocket message:', error);
      console.error('Message data that caused error:', data);
    }
  }, [onMessage, onComplete, onJobUpdate, onJobProgress, onError, onAgentEvent, toast, appendAgentTimeline, localizeHumanText, extractReasoningMessage, formatAgentName, onAgentComplete, callbacks, streamingMessage, onJobCreated]);

  // Планирование реконнекта с exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      toast({
        title: 'Соединение потеряно',
        description: 'Не удалось восстановить соединение с чатом.',
        status: 'warning',
        duration: 10000,
      });
      return;
    }

    reconnectAttempts.current++;

    const delay = reconnectDelay.current;


    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectDelay.current = Math.min(delay * 2, 30000); // Удваиваем задержку, max 30s
      connectRef.current?.();
    }, delay);
  }, [toast]);

  // Подключение к WebSocket
  const connect = useCallback(() => {
    // Предотвращаем множественные одновременные подключения
    if (connectingRef.current) {
      return;
    }

    if (!threadId) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }
    connectingRef.current = true;
    setConnectionState('connecting');

    // Небольшая задержка для предотвращения слишком быстрого создания соединений
    setTimeout(() => {
      if (!connectingRef.current) {
        return;
      }

      let wsUrl;
      try {
        wsUrl = getWebSocketUrl(threadId);
        wsRef.current = new WebSocket(wsUrl);

      // Обработчик открытия соединения
      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionState('connected');
        reconnectAttempts.current = 0;
        reconnectDelay.current = 1000; // Сброс задержки

        if (onConnect) onConnect(threadId);

        // Отправляем все сообщения из очереди
        if (messageQueueRef.current.length > 0) {
          messageQueueRef.current.forEach((queuedMessage) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              try {
                wsRef.current.send(JSON.stringify(queuedMessage));
              } catch (error) {
                console.error('❌ Failed to send queued message:', error);
              }
            }
          });
          messageQueueRef.current = []; // Очищаем очередь
        }

        // Сбрасываем флаг подключения
        connectingRef.current = false;
      };

      // Обработчик входящих сообщений
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleIncomingMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          console.error('Raw message that caused error:', event.data);
          if (onError) onError(error);
        }
      };

      // Обработчик закрытия соединения
      wsRef.current.onclose = (event) => {
        setIsConnected(false);
        setConnectionState('disconnected');
        setLastHeartbeat(null); // Сбрасываем heartbeat

        // Сбрасываем флаг подключения при закрытии
        connectingRef.current = false;

        // Очищаем heartbeat мониторинг
        if (heartbeatCheckRef.current) {
          clearInterval(heartbeatCheckRef.current);
          heartbeatCheckRef.current = null;
        }

        if (onDisconnect) onDisconnect(event);

        // Автореконнект при неожиданном разрыве
        // Код 1011 = Internal Error (server issue), 1006 = Abnormal Closure, 1000 = Normal Closure
        if (event.code === 1011) {
          toast({
            title: 'Ошибка сервера',
            description: 'WebSocket недоступен. Используется HTTP режим.',
            status: 'warning',
            duration: 3000,
          });
        } else if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          scheduleReconnect();
        } else {
        }
      };

      // Обработчик ошибок
      wsRef.current.onerror = (error) => {
        console.error('❌ === WebSocket ERROR EVENT ===');
        console.error('❌ Error object:', error);
        console.error('❌ WebSocket URL:', wsUrl);
        console.error('❌ WebSocket readyState:', wsRef.current?.readyState);
        console.error('❌ Thread ID:', threadId);
        console.error('❌ Is authenticated:', isAuthenticated);
        console.error('❌ Connection state before error:', connectionState);
        setConnectionState('error');

        // Сбрасываем флаг подключения при ошибке
        connectingRef.current = false;

        if (onError) onError(error);

        toast({
          title: 'Ошибка соединения',
          description: 'Проблема с подключением к чату. Попробуйте перезагрузить страницу.',
          status: 'error',
          duration: 5000,
        });
      };

      } catch (error) {
        console.error('❌ === WebSocket creation failed in setTimeout ===');
        console.error('❌ Error:', error);
        console.error('❌ Error stack:', error.stack);
        console.error('❌ Thread ID:', threadId);
        console.error('❌ URL that failed:', wsUrl);
        console.error('❌ wsUrl defined:', typeof wsUrl);
        setConnectionState('error');

        // Сбрасываем флаг подключения при ошибке
        connectingRef.current = false;

        if (onError) onError(error);
      }

    }, 50); // 50ms delay

  }, [threadId, getWebSocketUrl, onConnect, onDisconnect, onError, toast, handleIncomingMessage, scheduleReconnect, isAuthenticated, connectionState]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  // Очередь сообщений для отправки после подключения WebSocket
  const messageQueueRef = useRef([]);

  // Отправка сообщения через WebSocket
  const sendMessage = useCallback((message, selectedModel = null, inputType = null, options = {}) => {

    if (!message?.trim()) {
      return;
    }

    // Добавляем пользовательское сообщение в локальный state
    const userMessage = {
      id: `msg_${Date.now()}_${Math.random()}`,
      type: 'user',
      content: message.trim(),
      timestamp: new Date().toISOString(),
      ...(options.fileContext && { fileContext: true }),
    };
    setMessages(prev => [...prev, userMessage]);

    const messageData = {
      type: 'message',
      text: message.trim(),
      id: userMessage.id,
      timestamp: userMessage.timestamp,
      ...(selectedModel && { model: selectedModel }),
      ...(inputType && { input_type: inputType }),
      ...(options.webSearch && { web_search: true }),
      ...(options.deepResearch && { deep_research: true }),
      ...(options.fileContext && { file_context: options.fileContext }),
      ...(Array.isArray(options.fileIds) && options.fileIds.length && { file_ids: options.fileIds }),
      ...(options.routeOverride && { route_override: options.routeOverride }),
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(messageData));
      } catch (error) {
        console.error('Failed to send message via WebSocket:', error);
        messageQueueRef.current.push(messageData);
        if (onError) onError(error);
      }
    } else {
      messageQueueRef.current.push(messageData);
    }
  }, [onError]);

  // Принудительное переподключение
  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual reconnect');
    }
    setTimeout(() => connect(), 100);
  }, [connect]);

  // Очистка при размонтировании
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount');
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      // Сбрасываем флаг при размонтировании
      connectingRef.current = false;
    };
  }, [threadId]);

  // Автоматическое подключение при изменении threadId
  useEffect(() => {
    const threadIdChanged = prevThreadIdRef.current !== threadId;

    if (threadId && threadIdChanged) {
      // Очищаем очередь при смене thread, так как сообщения для старого thread бесполезны
      messageQueueRef.current = [];
      // Принудительно сбрасываем состояние перед подключением
      connectingRef.current = false;
      setConnectionState('disconnected');
      setIsConnected(false);
      connectRef.current?.();
    }

    prevThreadIdRef.current = threadId;

    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Thread ID changed');
        wsRef.current = null;
      }
      // Сбрасываем флаг и состояние при изменении threadId
      connectingRef.current = false;
      setConnectionState('disconnected');
      setIsConnected(false);
      setLastHeartbeat(null);
      setAgentTimeline([]);
      setAgentStatus(null);
    };
  }, [threadId, connect]);

  // Мониторинг heartbeat для обнаружения разрывов соединения
  useEffect(() => {
    if (connectionState === 'connected' && lastHeartbeat) {

      const checkHeartbeat = () => {
        const now = Date.now();
        const timeSinceLastHeartbeat = now - lastHeartbeat;
        const heartbeatTimeout = 30000; // 30 секунд

        if (timeSinceLastHeartbeat > heartbeatTimeout) {
          console.warn('💔 Heartbeat timeout - connection lost, reconnecting...');
          console.warn(`💔 Last heartbeat: ${timeSinceLastHeartbeat}ms ago`);
          setConnectionState('error');
          scheduleReconnect();
        }
      };

      heartbeatCheckRef.current = setInterval(checkHeartbeat, 10000); // Проверяем каждые 10 секунд

      return () => {
        if (heartbeatCheckRef.current) {
          clearInterval(heartbeatCheckRef.current);
          heartbeatCheckRef.current = null;
        }
      };
    }
  }, [connectionState, lastHeartbeat, scheduleReconnect]);

  return {
    // Состояние
    isConnected,
    connectionState,
    messages,
    currentJob,
    agentStatus,
    agentTimeline,
    reconnectAttempts: reconnectAttempts.current,

    // Методы
    sendMessage,
    reconnect,

    // Утилиты
    clearMessages: () => setMessages([]),
    getConnectionInfo: () => ({
      state: connectionState,
      attempts: reconnectAttempts.current,
      url: wsRef.current?.url,
      lastHeartbeat: lastHeartbeat ? new Date(lastHeartbeat).toISOString() : null
    })
  };
}
