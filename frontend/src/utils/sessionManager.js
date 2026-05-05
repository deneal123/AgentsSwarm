/**
 * GuestSessionManager - Управление гостевыми сессиями для неавторизованных пользователей
 *
 * Отвечает за:
 * - Создание и хранение гостевых сессий в localStorage
 * - Отслеживание лимитов запросов (10 бесплатных в сутки)
 * - Управление thread ID для чатов
 * - Автоматическую очистку истекших сессий
 */
class GuestSessionManager {
  constructor() {
    this.storageKey = 'guest_session';
    this.sessionDuration = 24 * 60 * 60 * 1000; // 24 часа
    this.maxRequestsPerDay = 10;
  }

  /**
   * Создает новую гостевую сессию
   * @returns {Object} Новая сессия
   */
  createGuestSession() {
    const sessionId = `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = new Date();
    const expiresAt = new Date(now.getTime() + this.sessionDuration);

    const session = {
      id: sessionId,
      createdAt: now.toISOString(),
      expiresAt: expiresAt.toISOString(),
      threadIds: [],
      requestCount: 0,
      limits: {
        maxRequests: this.maxRequestsPerDay,
        canGenerateCalendars: false, // Гости не могут генерировать календари
        lastReset: now.toISOString()
      }
    };

    localStorage.setItem(this.storageKey, JSON.stringify(session));
    return session;
  }

  /**
   * Получает текущую гостевую сессию с проверкой валидности
   * @returns {Object|null} Текущая сессия или null если истекла/не существует
   */
  getCurrentSession() {
    try {
      const sessionData = localStorage.getItem(this.storageKey);
      if (!sessionData) return null;

      const session = JSON.parse(sessionData);

      // Проверка истечения сессии
      if (new Date(session.expiresAt) < new Date()) {
        this.clearSession();
        return null;
      }

      // Автоматический сброс счетчика запросов раз в сутки
      this._resetDailyCounterIfNeeded(session);

      return session;
    } catch (error) {
      console.error('Error getting current session:', error);
      this.clearSession();
      return null;
    }
  }

  /**
   * Обновляет текущую сессию
   * @param {Object} updates - Обновления для сессии
   * @returns {Object|null} Обновленная сессия или null
   */
  updateSession(updates) {
    const session = this.getCurrentSession();
    if (!session) return null;

    const updatedSession = { ...session, ...updates };
    this.saveSession(updatedSession);
    return updatedSession;
  }

  /**
   * Сохраняет сессию в localStorage
   * @param {Object} session - Сессия для сохранения
   */
  saveSession(session) {
    localStorage.setItem(this.storageKey, JSON.stringify(session));
  }

  /**
   * Очищает текущую сессию
   */
  clearSession() {
    localStorage.removeItem(this.storageKey);
  }

  /**
   * Проверяет лимиты для текущей сессии
   * @returns {Object} Результат проверки { allowed, reason, remainingRequests }
   */
  checkLimits() {
    const session = this.getCurrentSession();

    if (!session) {
      return { allowed: false, reason: 'no_session' };
    }

    if (session.limits.requestCount >= session.limits.maxRequests) {
      return {
        allowed: false,
        reason: 'request_limit_exceeded',
        remainingRequests: 0,
        resetTime: new Date(session.limits.lastReset)
      };
    }

    return {
      allowed: true,
      remainingRequests: session.limits.maxRequests - session.limits.requestCount
    };
  }

  /**
   * Проверяет возможность генерации календарей
   * @returns {boolean} True если можно генерировать календари
   */
  canGenerateCalendars() {
    const session = this.getCurrentSession();
    return session?.limits.canGenerateCalendars || false;
  }

  /**
   * Инкрементирует счетчик запросов
   * @returns {number|null} Новый счетчик или null если сессия не найдена
   */
  incrementRequestCount() {
    const session = this.getCurrentSession();
    if (!session) return null;

    session.limits.requestCount += 1;
    this.saveSession(session);
    return session.limits.requestCount;
  }

  /**
   * Добавляет thread ID к сессии
   * @param {string} threadId - ID треда для добавления
   * @returns {Array|null} Массив thread IDs или null
   */
  addThreadId(threadId) {
    const session = this.getCurrentSession();
    if (!session) return null;

    if (!session.threadIds.includes(threadId)) {
      session.threadIds.push(threadId);
      this.saveSession(session);
    }

    return session.threadIds;
  }

  /**
   * Получает все thread IDs для сессии
   * @returns {Array} Массив thread IDs
   */
  getThreadIds() {
    const session = this.getCurrentSession();
    return session?.threadIds || [];
  }

  /**
   * Удаляет thread ID из сессии
   * @param {string} threadId - ID треда для удаления
   * @returns {Array|null} Обновленный массив thread IDs или null
   */
  removeThreadId(threadId) {
    const session = this.getCurrentSession();
    if (!session) return null;

    session.threadIds = session.threadIds.filter(id => id !== threadId);
    this.saveSession(session);
    return session.threadIds;
  }

  /**
   * Сбрасывает дневной счетчик запросов если прошло больше суток
   * @param {Object} session - Сессия для проверки
   * @private
   */
  _resetDailyCounterIfNeeded(session) {
    // Инициализируем limits если не существует
    if (!session.limits) {
      session.limits = {
        maxRequests: this.maxRequestsPerDay,
        requestCount: 0,
        canGenerateCalendars: false,
        lastReset: new Date().toISOString()
      };
      this.saveSession(session);
      return;
    }

    // Инициализируем недостающие поля
    if (typeof session.limits.maxRequests !== 'number') {
      session.limits.maxRequests = this.maxRequestsPerDay;
    }
    if (typeof session.limits.requestCount !== 'number') {
      session.limits.requestCount = 0;
    }
    if (typeof session.limits.canGenerateCalendars !== 'boolean') {
      session.limits.canGenerateCalendars = false;
    }

    // Если lastReset не существует, инициализируем его
    if (!session.limits.lastReset) {
      session.limits.lastReset = new Date().toISOString();
      this.saveSession(session);
      return;
    }

    const lastReset = new Date(session.limits.lastReset);
    const now = new Date();

    // Сбрасываем если прошел день
    if (now.getDate() !== lastReset.getDate() ||
        now.getMonth() !== lastReset.getMonth() ||
        now.getFullYear() !== lastReset.getFullYear()) {

      session.limits.requestCount = 0;
      session.limits.lastReset = now.toISOString();
      this.saveSession(session);
    }
  }

  /**
   * Получает статистику использования для текущей сессии
   * @returns {Object|null} Статистика или null
   */
  getUsageStats() {
    const session = this.getCurrentSession();
    if (!session) return null;

    const limits = session.limits;
    const remaining = Math.max(0, limits.maxRequests - limits.requestCount);

    return {
      totalRequests: limits.requestCount,
      remainingRequests: remaining,
      maxRequests: limits.maxRequests,
      canGenerateCalendars: limits.canGenerateCalendars,
      lastReset: new Date(limits.lastReset),
      sessionExpiresAt: new Date(session.expiresAt),
      threadCount: session.threadIds.length
    };
  }

  /**
   * Проверяет нужно ли показать предупреждение о приближающемся лимите
   * @param {number} threshold - Порог для предупреждения (по умолчанию 2)
   * @returns {boolean} True если нужно показать предупреждение
   */
  shouldShowLimitWarning(threshold = 2) {
    const session = this.getCurrentSession();
    if (!session) return false;

    const remaining = session.limits.maxRequests - session.limits.requestCount;
    return remaining <= threshold && remaining > 0;
  }
}

// Создаем и экспортируем единственный экземпляр
export const guestSessionManager = new GuestSessionManager();
