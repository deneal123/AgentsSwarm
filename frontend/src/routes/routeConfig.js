import { lazy } from "react";

export const APP_ROUTES = {
  ROOT: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  CHAT_THREAD: "/chat/:threadId",
  NOT_FOUND: "*",
};

export const APP_ROUTE_SEGMENTS = {
  LOGIN: "login",
  REGISTER: "register",
  CHAT_THREAD: "chat/:threadId",
};

const loadChatPage = () => import(/* webpackChunkName: "chat" */ "@pages/chat");
const loadLoginPage = () => import(/* webpackChunkName: "login" */ "@pages/login");
const loadSignUpPage = () => import(/* webpackChunkName: "signup" */ "@pages/signup");
const loadNotFoundPage = () => import(/* webpackChunkName: "notfound" */ "@pages/notFound");

export const ROUTE_LOADERS = {
  [APP_ROUTES.ROOT]: loadChatPage,
  [APP_ROUTES.LOGIN]: loadLoginPage,
  [APP_ROUTES.REGISTER]: loadSignUpPage,
  [APP_ROUTES.CHAT_THREAD]: loadChatPage,
  [APP_ROUTES.NOT_FOUND]: loadNotFoundPage,
};

export const RoutePages = {
  ChatPage: lazy(loadChatPage),
  LoginPage: lazy(loadLoginPage),
  SignUpPage: lazy(loadSignUpPage),
  NotFoundPage: lazy(loadNotFoundPage),
};

export const ROUTE_GUARDS = {
  PUBLIC: "public",
  AUTH_ONLY: "auth-only",
};

export const ROUTE_LAYOUTS = {
  PUBLIC: "public",
  PROTECTED: "protected",
};

export const ROUTE_CONFIG = [
  {
    path: APP_ROUTES.ROOT,
    page: "ChatPage",
    guard: ROUTE_GUARDS.AUTH_ONLY,
    layout: ROUTE_LAYOUTS.PROTECTED,
    preload: true,
  },
  {
    path: APP_ROUTES.CHAT_THREAD,
    page: "ChatPage",
    guard: ROUTE_GUARDS.AUTH_ONLY,
    layout: ROUTE_LAYOUTS.PROTECTED,
    preload: true,
  },
  {
    path: APP_ROUTES.LOGIN,
    page: "LoginPage",
    guard: ROUTE_GUARDS.PUBLIC,
    layout: ROUTE_LAYOUTS.PUBLIC,
    preload: true,
  },
  {
    path: APP_ROUTES.REGISTER,
    page: "SignUpPage",
    guard: ROUTE_GUARDS.PUBLIC,
    layout: ROUTE_LAYOUTS.PUBLIC,
    preload: true,
  },
  {
    path: APP_ROUTES.NOT_FOUND,
    page: "NotFoundPage",
    guard: ROUTE_GUARDS.PUBLIC,
    layout: ROUTE_LAYOUTS.PUBLIC,
    preload: false,
  },
];
