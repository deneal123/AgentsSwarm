import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';

// Analytics Context для управления сбором аналитики
const AnalyticsContext = createContext(null);

// Типы событий аналитики
export const ANALYTICS_EVENTS = {
  // User interactions
  USER_LOGIN: 'user_login',
  USER_LOGOUT: 'user_logout',
  USER_REGISTER: 'user_register',
  USER_PROFILE_UPDATE: 'user_profile_update',

  // Chat interactions
  CHAT_START: 'chat_start',
  CHAT_MESSAGE_SEND: 'chat_message_send',
  CHAT_MESSAGE_RECEIVE: 'chat_message_receive',
  CHAT_SEARCH: 'chat_search',
  CHAT_VOICE_RECORD: 'chat_voice_record',
  CHAT_FILE_UPLOAD: 'chat_file_upload',
  CHAT_REACTION_ADD: 'chat_reaction_add',

  // Feature usage
  FEATURE_THEME_CHANGE: 'feature_theme_change',
  FEATURE_SEARCH_OPEN: 'feature_search_open',
  FEATURE_HISTORY_VIEW: 'feature_history_view',
  FEATURE_VOICE_START: 'feature_voice_start',
  FEATURE_FEEDBACK_SUBMIT: 'feature_feedback_submit',

  // Performance events
  PERFORMANCE_PAGE_LOAD: 'performance_page_load',
  PERFORMANCE_COMPONENT_RENDER: 'performance_component_render',
  PERFORMANCE_API_CALL: 'performance_api_call',

  // Error events
  ERROR_JAVASCRIPT: 'error_javascript',
  ERROR_API: 'error_api',
  ERROR_NETWORK: 'error_network',
  ERROR_USER_FEEDBACK: 'error_user_feedback',

  // A/B testing
  AB_TEST_EXPOSURE: 'ab_test_exposure',
  AB_TEST_CONVERSION: 'ab_test_conversion',
};

// Уровни важности событий
export const EVENT_PRIORITIES = {
  LOW: 'low',       // Batch отправка, sampling возможен
  MEDIUM: 'medium', // Отправка в разумные сроки
  HIGH: 'high',     // Немедленная отправка
  CRITICAL: 'critical' // Всегда отправлять, никогда не терять
};

// Analytics Provider компонент
export function AnalyticsProvider({
  children,
  apiEndpoint = '/api/analytics/events',
  batchSize = 10,
  batchInterval = 30000, // 30 секунд
  samplingRate = 1.0, // 1.0 = 100% событий, 0.1 = 10%
  enablePrivacyMode = false,
  userId = null
}) {
  const [isEnabled, setIsEnabled] = useState(true);
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);

  // Очереди событий
  const eventQueue = useRef([]);
  const offlineQueue = useRef([]);

  // Таймеры
  const batchTimer = useRef(null);
  const retryTimer = useRef(null);

  // Статистика
  const stats = useRef({
    eventsTracked: 0,
    eventsSent: 0,
    eventsFailed: 0,
    batchesSent: 0,
    lastBatchTime: null,
  });

  // Проверка приватности и GDPR
  const shouldTrackEvent = useCallback((event) => {
    if (!isEnabled) return false;

    // Проверка sampling rate для низкоприоритетных событий
    if (event.priority === EVENT_PRIORITIES.LOW && Math.random() > samplingRate) {
      return false;
    }

    // Privacy mode фильтры
    if (enablePrivacyMode) {
      // Не отслеживать чувствительные данные в privacy mode
      const sensitiveFields = ['password', 'token', 'apiKey', 'creditCard'];
      const hasSensitiveData = Object.keys(event.properties || {}).some(key =>
        sensitiveFields.some(field => key.toLowerCase().includes(field))
      );
      if (hasSensitiveData) return false;
    }

    return true;
  }, [isEnabled, samplingRate, enablePrivacyMode]);

  // Отправка событий на сервер
  const sendEvents = useCallback(async (events, isRetry = false) => {
    if (!navigator.onLine && !isRetry) {
      // Сохранить в offline queue
      offlineQueue.current.push(...events);
      return;
    }

    try {
      const payload = {
        sessionId,
        userId,
        events: events.map(event => ({
          ...event,
          timestamp: event.timestamp || new Date().toISOString(),
          sessionId,
          userId,
        })),
        metadata: {
          userAgent: navigator.userAgent,
          url: window.location.href,
          referrer: document.referrer,
          screenSize: `${window.screen.width}x${window.screen.height}`,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        }
      };

      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Analytics API error: ${response.status}`);
      }

      stats.current.eventsSent += events.length;
      stats.current.batchesSent += 1;
      stats.current.lastBatchTime = new Date();

      console.log(`Analytics: Sent ${events.length} events`);

    } catch (error) {
      console.error('Failed to send analytics events:', error);
      stats.current.eventsFailed += events.length;

      // Повторить через 30 секунд при ошибке
      if (!isRetry) {
        setTimeout(() => sendEvents(events, true), 30000);
      }
    }
  }, [apiEndpoint, sessionId, userId]);

  // Пакетная отправка событий
  const flushQueue = useCallback(() => {
    if (eventQueue.current.length === 0) return;

    const eventsToSend = [...eventQueue.current];
    eventQueue.current = [];

    sendEvents(eventsToSend);
  }, [sendEvents]);

  // Добавление события в очередь
  const trackEvent = useCallback((eventName, properties = {}, priority = EVENT_PRIORITIES.MEDIUM) => {
    const event = {
      name: eventName,
      properties: {
        ...properties,
        url: window.location.pathname,
        timestamp: new Date().toISOString(),
      },
      priority,
      id: `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };

    if (!shouldTrackEvent(event)) return;

    eventQueue.current.push(event);
    stats.current.eventsTracked += 1;

    // Отправить критические события немедленно
    if (priority === EVENT_PRIORITIES.CRITICAL) {
      sendEvents([event]);
    } else if (priority === EVENT_PRIORITIES.HIGH) {
      // Отправить high priority события через 1 секунду
      setTimeout(() => {
        const highPriorityEvents = eventQueue.current.filter(e => e.priority === EVENT_PRIORITIES.HIGH);
        if (highPriorityEvents.length > 0) {
          eventQueue.current = eventQueue.current.filter(e => e.priority !== EVENT_PRIORITIES.HIGH);
          sendEvents(highPriorityEvents);
        }
      }, 1000);
    }

    // Проверить размер очереди для немедленной отправки
    if (eventQueue.current.length >= batchSize) {
      flushQueue();
    }
  }, [shouldTrackEvent, sendEvents, batchSize, flushQueue]);

  // Отправка offline событий при восстановлении соединения
  const sendOfflineEvents = useCallback(() => {
    if (offlineQueue.current.length > 0 && navigator.onLine) {
      const offlineEvents = [...offlineQueue.current];
      offlineQueue.current = [];
      sendEvents(offlineEvents);
    }
  }, [sendEvents]);

  // Инициализация
  useEffect(() => {
    // Начать периодическую отправку
    batchTimer.current = setInterval(flushQueue, batchInterval);

    // Обработчик восстановления соединения
    const handleOnline = () => {
      console.log('Analytics: Connection restored, sending offline events');
      sendOfflineEvents();
    };

    window.addEventListener('online', handleOnline);

    // Отправка события инициализации
    trackEvent('analytics_initialized', {
      sessionId,
      userId,
      timestamp: new Date().toISOString(),
    }, EVENT_PRIORITIES.LOW);

    return () => {
      if (batchTimer.current) clearInterval(batchTimer.current);
      if (retryTimer.current) clearTimeout(retryTimer.current);
      window.removeEventListener('online', handleOnline);

      // Отправить оставшиеся события при размонтировании
      flushQueue();
    };
  }, [batchInterval, flushQueue, sendOfflineEvents, trackEvent, sessionId, userId]);

  // Обработчик перед закрытием страницы
  useEffect(() => {
    const handleBeforeUnload = () => {
      // Синхронная отправка критических событий
      if (eventQueue.current.length > 0) {
        const criticalEvents = eventQueue.current.filter(e => e.priority === EVENT_PRIORITIES.CRITICAL);
        if (criticalEvents.length > 0) {
          // Используем sendBeacon для надежной доставки
          const blob = new Blob([JSON.stringify({
            sessionId,
            userId,
            events: criticalEvents,
            beforeUnload: true
          })], { type: 'application/json' });

          navigator.sendBeacon(apiEndpoint, blob);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [apiEndpoint, sessionId, userId]);

  // Context value
  const contextValue = {
    // State
    isEnabled,
    sessionId,
    stats: stats.current,

    // Methods
    trackEvent,
    setEnabled: setIsEnabled,
    flushQueue,
    getStats: () => ({ ...stats.current }),

    // Constants
    events: ANALYTICS_EVENTS,
    priorities: EVENT_PRIORITIES,
  };

  return (
    <AnalyticsContext.Provider value={contextValue}>
      {children}
    </AnalyticsContext.Provider>
  );
}

// Hook для использования Analytics Context
export function useAnalytics() {
  const context = useContext(AnalyticsContext);
  if (!context) {
    throw new Error('useAnalytics must be used within an AnalyticsProvider');
  }
  return context;
}

// Hook для отслеживания событий с автоматическим контекстом
export function useEventTracker() {
  const { trackEvent, events, priorities } = useAnalytics();

  const track = useCallback((eventName, properties = {}, priority = priorities.MEDIUM) => {
    trackEvent(eventName, properties, priority);
  }, [trackEvent, priorities]);

  return {
    track,
    events,
    priorities,
  };
}

export default AnalyticsContext;
