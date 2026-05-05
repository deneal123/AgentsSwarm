/**
 * useRoutePreload — хук для предзагрузки маршрутов
 * Улучшает UX за счёт предзагрузки страниц при hover на ссылки
 */

import { useCallback } from "react";

// Карта preload функций для маршрутов
const preloadMap = {
  // "/datasets": () => import(/* webpackChunkName: "datasets" */ "@pages/datasets"),
  // "/training": () => import(/* webpackChunkName: "training" */ "@pages/training"),
  // "/artifacts": () => import(/* webpackChunkName: "artifacts" */ "@pages/artifacts"),
  // "/metrics": () => import(/* webpackChunkName: "metrics" */ "@pages/metrics"),
  "/login": () => import(/* webpackChunkName: "login" */ "@pages/login"),
  "/register": () => import(/* webpackChunkName: "signup" */ "@pages/signup"),
};

// Кэш уже загруженных маршрутов
const loadedRoutes = new Set();

/**
 * Предзагружает маршрут по пути
 * @param {string} path - Путь маршрута
 */
export const preloadRoute = (path) => {
  // Не загружаем повторно
  if (loadedRoutes.has(path)) return;

  const preloader = preloadMap[path];
  if (preloader) {
    preloader()
      .then(() => {
        loadedRoutes.add(path);
      })
      .catch(() => {
        // Игнорируем ошибки preload - это не критично
      });
  }
};

/**
 * Хук для получения обработчика preload
 * @returns {Function} Функция preload для использования в onMouseEnter
 */
export function useRoutePreload() {
  const handlePreload = useCallback((path) => {
    // Используем requestIdleCallback для оптимизации
    if (typeof window !== "undefined" && "requestIdleCallback" in window) {
      window.requestIdleCallback(() => preloadRoute(path), { timeout: 2000 });
    } else {
      // Fallback с небольшой задержкой
      setTimeout(() => preloadRoute(path), 100);
    }
  }, []);

  return handlePreload;
}

/**
 * Предзагружает критичные маршруты при загрузке приложения
 * Вызывать в App.js после монтирования
 */
export const preloadCriticalRoutes = () => {
  if (typeof window === "undefined") return;

  // Загружаем в idle time
  const preloader = () => {
    // Основные маршруты для аутентифицированных пользователей
    preloadRoute("/datasets");
    preloadRoute("/training");
  };

  if ("requestIdleCallback" in window) {
    window.requestIdleCallback(preloader, { timeout: 5000 });
  } else {
    setTimeout(preloader, 2000);
  }
};

export default useRoutePreload;
