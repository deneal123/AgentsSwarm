import { useState, useEffect, useCallback } from 'react';
import { guestSessionManager } from '../utils/sessionManager';

/**
 * useGuestSession - React хук для работы с гостевыми сессиями
 *
 * Предоставляет:
 * - Автоматическую инициализацию сессии
 * - Методы для работы с лимитами и thread IDs
 * - React-friendly state management
 */
export function useGuestSession() {
  const [session, setSession] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Инициализация сессии при монтировании
  useEffect(() => {
    const initSession = () => {
      try {
        let currentSession = guestSessionManager.getCurrentSession();

        // Создаем новую сессию если текущей нет
        if (!currentSession) {
          currentSession = guestSessionManager.createGuestSession();
        }

        setSession(currentSession);
        setError(null);
      } catch (err) {
        console.error('Failed to initialize guest session:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    initSession();
  }, []);

  // Обновление состояния сессии
  const refreshSession = useCallback(() => {
    try {
      const currentSession = guestSessionManager.getCurrentSession();
      setSession(currentSession);
      setError(null);
    } catch (err) {
      console.error('Failed to refresh session:', err);
      setError(err.message);
    }
  }, []);

  // Проверка лимитов
  const checkLimits = useCallback(() => {
    return guestSessionManager.checkLimits();
  }, []);

  // Инкремент счетчика запросов
  const incrementRequests = useCallback(() => {
    try {
      const newCount = guestSessionManager.incrementRequestCount();
      if (newCount !== null) {
        refreshSession(); // Обновляем локальный state
      }
      return newCount;
    } catch (err) {
      console.error('Failed to increment request count:', err);
      setError(err.message);
      return null;
    }
  }, [refreshSession]);

  // Добавление thread ID
  const addThreadId = useCallback((threadId) => {
    try {
      const threadIds = guestSessionManager.addThreadId(threadId);
      if (threadIds !== null) {
        refreshSession(); // Обновляем локальный state
      }
      return threadIds;
    } catch (err) {
      console.error('Failed to add thread ID:', err);
      setError(err.message);
      return null;
    }
  }, [refreshSession]);

  // Удаление thread ID
  const removeThreadId = useCallback((threadId) => {
    try {
      const threadIds = guestSessionManager.removeThreadId(threadId);
      if (threadIds !== null) {
        refreshSession(); // Обновляем локальный state
      }
      return threadIds;
    } catch (err) {
      console.error('Failed to remove thread ID:', err);
      setError(err.message);
      return null;
    }
  }, [refreshSession]);

  // Проверка возможности генерации календарей
  const canGenerateCalendars = useCallback(() => {
    return guestSessionManager.canGenerateCalendars();
  }, []);

  // Получение статистики использования
  const getUsageStats = useCallback(() => {
    return guestSessionManager.getUsageStats();
  }, []);

  // Проверка нужно ли показать предупреждение о лимите
  const shouldShowLimitWarning = useCallback((threshold = 2) => {
    return guestSessionManager.shouldShowLimitWarning(threshold);
  }, []);

  // Очистка сессии
  const clearSession = useCallback(() => {
    try {
      guestSessionManager.clearSession();
      setSession(null);
      setError(null);
    } catch (err) {
      console.error('Failed to clear session:', err);
      setError(err.message);
    }
  }, []);

  // Создание новой сессии
  const createNewSession = useCallback(() => {
    try {
      const newSession = guestSessionManager.createGuestSession();
      setSession(newSession);
      setError(null);
      return newSession;
    } catch (err) {
      console.error('Failed to create new session:', err);
      setError(err.message);
      return null;
    }
  }, []);

  return {
    // State
    session,
    isLoading,
    error,

    // Methods
    refreshSession,
    checkLimits,
    incrementRequests,
    addThreadId,
    removeThreadId,
    canGenerateCalendars,
    getUsageStats,
    shouldShowLimitWarning,
    clearSession,
    createNewSession,

    // Computed properties
    remainingRequests: (() => {
      if (!session || !session.limits) return 10; // Default for new users

      const maxRequests = Number(session.limits.maxRequests);
      const requestCount = Number(session.limits.requestCount);

      if (isNaN(maxRequests) || isNaN(requestCount)) return 10;

      return Math.max(0, maxRequests - requestCount);
    })(),
    hasReachedLimit: session ? session.limits.requestCount >= session.limits.maxRequests : false,
    sessionId: session?.id || null,
    threadIds: session?.threadIds || [],
    threadCount: session?.threadIds?.length || 0,
  };
}
