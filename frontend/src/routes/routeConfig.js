import { lazy } from 'react';
import { APP_ROUTES, ROUTE_GUARDS, ROUTE_LAYOUTS } from '../app/router';

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
  { path: APP_ROUTES.LOGIN, page: 'LoginPage', guard: ROUTE_GUARDS.PUBLIC, layout: ROUTE_LAYOUTS.PUBLIC, preload: 'intent' },
  { path: APP_ROUTES.REGISTER, page: 'SignUpPage', guard: ROUTE_GUARDS.PUBLIC, layout: ROUTE_LAYOUTS.PUBLIC, preload: 'intent' },
  { path: APP_ROUTES.NOT_FOUND, page: 'NotFoundPage', guard: ROUTE_GUARDS.PUBLIC, layout: ROUTE_LAYOUTS.PUBLIC, preload: false },
];
