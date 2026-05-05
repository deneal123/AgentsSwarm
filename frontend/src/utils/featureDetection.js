/**
 * Feature Detection утилиты для кроссплатформенной совместимости
 * Используются для определения возможностей браузера и адаптации функционала
 */

/**
 * Проверяет поддержку формата WebP
 * @returns {boolean}
 */
export const supportsWebP = () => {
  if (typeof document === "undefined") return false;
  const canvas = document.createElement("canvas");
  return canvas.toDataURL("image/webp").indexOf("data:image/webp") === 0;
};

/**
 * Проверяет поддержку CSS Grid
 * @returns {boolean}
 */
export const supportsCSSGrid = () => {
  if (typeof CSS === "undefined") return false;
  return CSS.supports("display", "grid");
};

/**
 * Проверяет поддержку CSS Flexbox Gap
 * @returns {boolean}
 */
export const supportsFlexGap = () => {
  if (typeof document === "undefined") return false;
  const flex = document.createElement("div");
  flex.style.display = "flex";
  flex.style.gap = "1px";
  return flex.style.gap === "1px";
};

/**
 * Проверяет, предпочитает ли пользователь уменьшенное движение
 * @returns {boolean}
 */
export const prefersReducedMotion = () => {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
};

/**
 * Проверяет, является ли устройство сенсорным
 * @returns {boolean}
 */
export const isTouchDevice = () => {
  if (typeof window === "undefined") return false;
  return "ontouchstart" in window || navigator.maxTouchPoints > 0;
};

/**
 * Проверяет поддержку IntersectionObserver
 * @returns {boolean}
 */
export const supportsIntersectionObserver = () => {
  return typeof window !== "undefined" && "IntersectionObserver" in window;
};

/**
 * Проверяет поддержку ResizeObserver
 * @returns {boolean}
 */
export const supportsResizeObserver = () => {
  return typeof window !== "undefined" && "ResizeObserver" in window;
};

/**
 * Проверяет поддержку CSS backdrop-filter
 * @returns {boolean}
 */
export const supportsBackdropFilter = () => {
  if (typeof CSS === "undefined") return false;
  return (
    CSS.supports("backdrop-filter", "blur(10px)") ||
    CSS.supports("-webkit-backdrop-filter", "blur(10px)")
  );
};

/**
 * Проверяет поддержку requestIdleCallback
 * @returns {boolean}
 */
export const supportsIdleCallback = () => {
  return typeof window !== "undefined" && "requestIdleCallback" in window;
};

/**
 * Определяет тип соединения (для оптимизации загрузки)
 * @returns {"slow" | "fast" | "unknown"}
 */
export const getConnectionType = () => {
  if (typeof navigator === "undefined") return "unknown";
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (!connection) return "unknown";

  const slowConnections = ["slow-2g", "2g", "3g"];
  if (slowConnections.includes(connection.effectiveType)) {
    return "slow";
  }
  return "fast";
};

/**
 * Проверяет, включён ли режим экономии данных
 * @returns {boolean}
 */
export const isDataSaverEnabled = () => {
  if (typeof navigator === "undefined") return false;
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  return connection?.saveData === true;
};

/**
 * Проверяет поддержку Service Worker
 * @returns {boolean}
 */
export const supportsServiceWorker = () => {
  return typeof navigator !== "undefined" && "serviceWorker" in navigator;
};

/**
 * Получает информацию о браузере
 * @returns {{ name: string, version: string }}
 */
export const getBrowserInfo = () => {
  if (typeof navigator === "undefined") {
    return { name: "unknown", version: "unknown" };
  }

  const ua = navigator.userAgent;
  let name = "unknown";
  let version = "unknown";

  if (ua.includes("Firefox/")) {
    name = "Firefox";
    version = ua.split("Firefox/")[1]?.split(" ")[0] || "unknown";
  } else if (ua.includes("Edg/")) {
    name = "Edge";
    version = ua.split("Edg/")[1]?.split(" ")[0] || "unknown";
  } else if (ua.includes("Chrome/")) {
    name = "Chrome";
    version = ua.split("Chrome/")[1]?.split(" ")[0] || "unknown";
  } else if (ua.includes("Safari/") && !ua.includes("Chrome")) {
    name = "Safari";
    version = ua.split("Version/")[1]?.split(" ")[0] || "unknown";
  }

  return { name, version };
};

/**
 * Проверяет, находится ли пользователь на мобильном устройстве
 * @returns {boolean}
 */
export const isMobileDevice = () => {
  if (typeof navigator === "undefined") return false;
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
};

/**
 * Объект с результатами всех проверок (ленивая инициализация)
 */
let _featureCache = null;

export const getFeatures = () => {
  if (_featureCache) return _featureCache;

  _featureCache = {
    webp: supportsWebP(),
    cssGrid: supportsCSSGrid(),
    flexGap: supportsFlexGap(),
    reducedMotion: prefersReducedMotion(),
    touch: isTouchDevice(),
    intersectionObserver: supportsIntersectionObserver(),
    resizeObserver: supportsResizeObserver(),
    backdropFilter: supportsBackdropFilter(),
    idleCallback: supportsIdleCallback(),
    connectionType: getConnectionType(),
    dataSaver: isDataSaverEnabled(),
    serviceWorker: supportsServiceWorker(),
    mobile: isMobileDevice(),
    browser: getBrowserInfo(),
  };

  return _featureCache;
};

export default getFeatures;
