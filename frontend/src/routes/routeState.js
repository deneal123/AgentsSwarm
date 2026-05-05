import { APP_ROUTES } from "./routeConfig";

const AUTH_ROUTES = new Set([APP_ROUTES.LOGIN, APP_ROUTES.REGISTER]);

export const isAuthRoute = (pathname = "") => AUTH_ROUTES.has(pathname);

export const isChatRoute = (pathname = "") => {
  return pathname === APP_ROUTES.ROOT || pathname.startsWith("/chat/");
};

export const shouldUseFullWidthLayout = (pathname = "") => {
  return isChatRoute(pathname) || isAuthRoute(pathname);
};
