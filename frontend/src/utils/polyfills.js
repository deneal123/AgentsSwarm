/**
 * Полифиллы для обеспечения кроссбраузерной совместимости
 * Импортируйте этот файл в начале приложения (index.js)
 */

// Полифилл для requestIdleCallback
if (typeof window !== "undefined" && !("requestIdleCallback" in window)) {
  window.requestIdleCallback = function (callback, options) {
    const start = Date.now();
    return setTimeout(function () {
      callback({
        didTimeout: false,
        timeRemaining: function () {
          return Math.max(0, 50 - (Date.now() - start));
        },
      });
    }, options?.timeout || 1);
  };

  window.cancelIdleCallback = function (id) {
    clearTimeout(id);
  };
}

// Полифилл для Array.prototype.at()
if (!Array.prototype.at) {
  // eslint-disable-next-line no-extend-native
  Array.prototype.at = function (index) {
    const len = this.length;
    const relativeIndex = index >= 0 ? index : len + index;
    if (relativeIndex < 0 || relativeIndex >= len) return undefined;
    return this[relativeIndex];
  };
}

// Полифилл для Object.hasOwn()
if (!Object.hasOwn) {
  Object.hasOwn = function (obj, prop) {
    return Object.prototype.hasOwnProperty.call(obj, prop);
  };
}

// Полифилл для String.prototype.replaceAll()
if (!String.prototype.replaceAll) {
  // eslint-disable-next-line no-extend-native
  String.prototype.replaceAll = function (search, replacement) {
    return this.split(search).join(replacement);
  };
}

// Проверка поддержки API (для информации, без полифиллов)
export const checkAPISupport = () => {
  const support = {
    IntersectionObserver: typeof window !== "undefined" && "IntersectionObserver" in window,
    ResizeObserver: typeof window !== "undefined" && "ResizeObserver" in window,
    requestIdleCallback: typeof window !== "undefined" && "requestIdleCallback" in window,
  };

  if (process.env.NODE_ENV === "development") {
    const unsupported = Object.entries(support)
      .filter(([, supported]) => !supported)
      .map(([name]) => name);

    if (unsupported.length > 0) {
      console.info(`[Polyfills] APIs not natively supported: ${unsupported.join(", ")}`);
    }
  }

  return support;
};

// Автоматическая проверка при импорте
if (typeof window !== "undefined") {
  checkAPISupport();
}

export default checkAPISupport;
