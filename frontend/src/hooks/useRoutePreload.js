import { APP_ROUTES, ROUTE_CONFIG, ROUTE_LOADERS } from "../routes/routeConfig";

const preloadMap = ROUTE_CONFIG.filter((route) => route.preload).reduce((acc, route) => {
  const loader = ROUTE_LOADERS[route.path];
  if (loader) {
    acc[route.path] = loader;
  }
  return acc;
}, {});

const loadedRoutes = new Set();

export const preloadRoute = (path) => {
  if (loadedRoutes.has(path)) return;
  const preloader = preloadMap[path];
  if (!preloader) return;
  preloader()
    .then(() => loadedRoutes.add(path))
    .catch(() => undefined);
};

export const preloadCriticalRoutes = () => {
  if (typeof window === "undefined") return;
  const preloader = () => {
    preloadRoute(APP_ROUTES.ROOT);
  };
  if ("requestIdleCallback" in window) {
    window.requestIdleCallback(preloader, { timeout: 5000 });
    return;
  }
  setTimeout(preloader, 2000);
};
