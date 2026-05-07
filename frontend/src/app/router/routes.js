import { lazy } from 'react';

export const APP_ROUTES = {
  ROOT: '/',
  LOGIN: '/login',
  SIGNUP: '/signup',
  REGISTER: '/register',
  CHAT_THREAD: '/chat/:threadId',
  NOT_FOUND: '*',
};

export const ROUTE_GUARDS = {
  PUBLIC: 'public',
  GUEST_ONLY: 'guest-only',
  AUTH_ONLY: 'auth-only',
  FEATURE_FLAG: 'feature-flag',
};

export const ROUTE_LAYOUTS = {
  PUBLIC: 'public',
  PROTECTED: 'protected',
};

const loadChatPage = () => import(/* webpackChunkName: "route-chat" */ '@pages/chat');
const loadLoginPage = () => import(/* webpackChunkName: "route-login" */ '@pages/login');
const loadSignUpPage = () => import(/* webpackChunkName: "route-signup" */ '@pages/signup');
const loadNotFoundPage = () => import(/* webpackChunkName: "route-notfound" */ '@pages/notFound');

export const ROUTE_LOADERS = {
  chat: loadChatPage,
  login: loadLoginPage,
  signup: loadSignUpPage,
  notfound: loadNotFoundPage,
};

export const RoutePages = {
  ChatPage: lazy(loadChatPage),
  LoginPage: lazy(loadLoginPage),
  SignUpPage: lazy(loadSignUpPage),
  NotFoundPage: lazy(loadNotFoundPage),
};

export const ROUTE_CONFIG = [
  { path: APP_ROUTES.ROOT, page: 'ChatPage', guard: ROUTE_GUARDS.AUTH_ONLY, layout: ROUTE_LAYOUTS.PROTECTED, preload: 'idle' },
  { path: APP_ROUTES.CHAT_THREAD, page: 'ChatPage', guard: ROUTE_GUARDS.AUTH_ONLY, layout: ROUTE_LAYOUTS.PROTECTED, preload: false },
  { path: APP_ROUTES.LOGIN, page: 'LoginPage', guard: ROUTE_GUARDS.GUEST_ONLY, layout: ROUTE_LAYOUTS.PUBLIC, preload: 'intent' },
  { path: APP_ROUTES.SIGNUP, page: 'SignUpPage', guard: ROUTE_GUARDS.GUEST_ONLY, layout: ROUTE_LAYOUTS.PUBLIC, preload: 'intent' },
  { path: APP_ROUTES.REGISTER, redirectTo: APP_ROUTES.SIGNUP, guard: ROUTE_GUARDS.PUBLIC, layout: ROUTE_LAYOUTS.PUBLIC, preload: false },
];

export const FALLBACK_ROUTE = {
  path: APP_ROUTES.NOT_FOUND,
  page: 'NotFoundPage',
  guard: ROUTE_GUARDS.PUBLIC,
};

const AUTH_ROUTES = new Set([APP_ROUTES.LOGIN, APP_ROUTES.SIGNUP, APP_ROUTES.REGISTER]);

export const isAuthRoute = (pathname = '') => AUTH_ROUTES.has(pathname);

export const isChatRoute = (pathname = '') => pathname === APP_ROUTES.ROOT || pathname.startsWith('/chat/');

export const shouldUseFullWidthLayout = (pathname = '') => isChatRoute(pathname) || isAuthRoute(pathname);
