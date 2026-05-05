import { useCallback } from "react";

const preloadMap = {
  "/": () => import(/* webpackChunkName: "chat" */ "@pages/chat"),
  "/home": () => import(/* webpackChunkName: "home" */ "@pages/home"),
  "/info": () => import(/* webpackChunkName: "info" */ "@pages/info"),
  "/documents": () => import(/* webpackChunkName: "documents" */ "@features/documents/DocumentsPage"),
  "/login": () => import(/* webpackChunkName: "login" */ "@pages/login"),
  "/register": () => import(/* webpackChunkName: "signup" */ "@pages/signup"),
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

export function useRoutePreload() {
  return useCallback((path) => {
    if (typeof window !== "undefined" && "requestIdleCallback" in window) {
      window.requestIdleCallback(() => preloadRoute(path), { timeout: 2000 });
      return;
    }
    setTimeout(() => preloadRoute(path), 100);
  }, []);
}

export const preloadCriticalRoutes = () => {
  if (typeof window === "undefined") return;
  const preloader = () => {
    preloadRoute("/");
    preloadRoute("/home");
  };
  if ("requestIdleCallback" in window) {
    window.requestIdleCallback(preloader, { timeout: 5000 });
    return;
  }
  setTimeout(preloader, 2000);
};

export default useRoutePreload;
