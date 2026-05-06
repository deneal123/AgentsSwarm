import { lazy } from "react";

export const APP_ROUTES = {
  ROOT: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  CHAT_THREAD: "/chat/:threadId",
};

export const APP_ROUTE_SEGMENTS = {
  LOGIN: "login",
  REGISTER: "register",
  CHAT_THREAD: "chat/:threadId",
};

export const ROUTE_LOADERS = {
  [APP_ROUTES.ROOT]: () => import(/* webpackChunkName: "chat" */ "@pages/chat"),
  [APP_ROUTES.LOGIN]: () => import(/* webpackChunkName: "login" */ "@pages/login"),
  [APP_ROUTES.REGISTER]: () => import(/* webpackChunkName: "signup" */ "@pages/signup"),
  NOT_FOUND: () => import(/* webpackChunkName: "notfound" */ "@pages/notFound"),
};

export const RoutePages = {
  ChatPage: lazy(ROUTE_LOADERS[APP_ROUTES.ROOT]),
  LoginPage: lazy(ROUTE_LOADERS[APP_ROUTES.LOGIN]),
  SignUpPage: lazy(ROUTE_LOADERS[APP_ROUTES.REGISTER]),
  NotFoundPage: lazy(ROUTE_LOADERS.NOT_FOUND),
};
