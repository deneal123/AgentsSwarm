import { APP_ROUTES, ROUTE_LOADERS } from "../routes/routeConfig";

const preloadMap = {
  [APP_ROUTES.ROOT]: ROUTE_LOADERS[APP_ROUTES.ROOT],
  [APP_ROUTES.INFO]: ROUTE_LOADERS[APP_ROUTES.INFO],
  [APP_ROUTES.DOCUMENTS]: ROUTE_LOADERS[APP_ROUTES.DOCUMENTS],
  [APP_ROUTES.LOGIN]: ROUTE_LOADERS[APP_ROUTES.LOGIN],
  [APP_ROUTES.REGISTER]: ROUTE_LOADERS[APP_ROUTES.REGISTER],
};

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

