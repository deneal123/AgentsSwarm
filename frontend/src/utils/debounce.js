/**
 * Утилиты для дебаунса и троттлинга
 * Используются для оптимизации частых вызовов функций
 */

/**
 * Создаёт дебаунсированную версию функции
 * Функция будет вызвана только после того, как пройдёт указанное время
 * с момента последнего вызова
 *
 * @param {Function} func - Функция для дебаунса
 * @param {number} wait - Время ожидания в миллисекундах
 * @param {boolean} immediate - Вызвать немедленно при первом вызове
 * @returns {Function} Дебаунсированная функция с методом cancel()
 */
export function debounce(func, wait, immediate = false) {
  let timeout = null;
  let result;

  const debounced = function (...args) {
    const context = this;
    const later = () => {
      timeout = null;
      if (!immediate) {
        result = func.apply(context, args);
      }
    };

    const callNow = immediate && !timeout;

    if (timeout) {
      clearTimeout(timeout);
    }

    timeout = setTimeout(later, wait);

    if (callNow) {
      result = func.apply(context, args);
    }

    return result;
  };

  debounced.cancel = () => {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
    }
  };

  debounced.flush = () => {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
      result = func.apply(this, []);
    }
    return result;
  };

  return debounced;
}

/**
 * Создаёт троттлированную версию функции
 * Функция будет вызываться не чаще, чем раз в указанный интервал
 *
 * @param {Function} func - Функция для троттлинга
 * @param {number} limit - Минимальный интервал между вызовами в миллисекундах
 * @param {object} options - Опции
 * @param {boolean} options.leading - Вызвать в начале интервала
 * @param {boolean} options.trailing - Вызвать в конце интервала
 * @returns {Function} Троттлированная функция с методом cancel()
 */
export function throttle(func, limit, options = {}) {
  const { leading = true, trailing = true } = options;
  let timeout = null;
  let lastArgs = null;
  let lastContext = null;
  let result;
  let lastCallTime = 0;

  const invokeFunc = (time) => {
    const args = lastArgs;
    const context = lastContext;
    lastArgs = null;
    lastContext = null;
    lastCallTime = time;
    result = func.apply(context, args);
    return result;
  };

  const trailingEdge = (time) => {
    timeout = null;
    if (trailing && lastArgs) {
      return invokeFunc(time);
    }
    lastArgs = null;
    lastContext = null;
    return result;
  };

  const throttled = function (...args) {
    const now = Date.now();
    const isInvoking = lastCallTime === 0 && !leading;

    if (isInvoking) {
      lastCallTime = now;
    }

    const remaining = limit - (now - lastCallTime);
    lastArgs = args;
    lastContext = this;

    if (remaining <= 0 || remaining > limit) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      lastCallTime = now;
      result = func.apply(this, args);
      if (!timeout) {
        lastArgs = null;
        lastContext = null;
      }
    } else if (!timeout && trailing) {
      timeout = setTimeout(() => trailingEdge(Date.now()), remaining);
    }

    return result;
  };

  throttled.cancel = () => {
    if (timeout) {
      clearTimeout(timeout);
    }
    lastCallTime = 0;
    timeout = null;
    lastArgs = null;
    lastContext = null;
  };

  return throttled;
}

/**
 * React хук для дебаунса значения
 * @param {*} value - Значение для дебаунса
 * @param {number} delay - Задержка в миллисекундах
 * @returns {*} Дебаунсированное значение
 */
import { useState, useEffect } from "react";

export function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * React хук для создания дебаунсированного callback
 * @param {Function} callback - Callback для дебаунса
 * @param {number} delay - Задержка в миллисекундах
 * @param {Array} deps - Зависимости
 * @returns {Function} Дебаунсированный callback
 */
import { useCallback, useRef } from "react";

export function useDebouncedCallback(callback, delay, deps = []) {
  const callbackRef = useRef(callback);
  const timeoutRef = useRef(null);

  // Обновляем ref при изменении callback
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Очистка при размонтировании
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return useCallback(
    (...args) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [delay, ...deps],
  );
}

/**
 * React хук для создания троттлированного callback
 * @param {Function} callback - Callback для троттлинга
 * @param {number} limit - Минимальный интервал в миллисекундах
 * @param {Array} deps - Зависимости
 * @returns {Function} Троттлированный callback
 */
export function useThrottledCallback(callback, limit, deps = []) {
  const callbackRef = useRef(callback);
  const lastCallRef = useRef(0);
  const timeoutRef = useRef(null);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return useCallback(
    (...args) => {
      const now = Date.now();
      const remaining = limit - (now - lastCallRef.current);

      if (remaining <= 0) {
        lastCallRef.current = now;
        callbackRef.current(...args);
      } else if (!timeoutRef.current) {
        timeoutRef.current = setTimeout(() => {
          lastCallRef.current = Date.now();
          timeoutRef.current = null;
          callbackRef.current(...args);
        }, remaining);
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [limit, ...deps],
  );
}
