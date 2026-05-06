export const APP_ROUTES = {
  ROOT: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  CHAT_THREAD: '/chat/:threadId',
  NOT_FOUND: '*',
};

export const ROUTE_GUARDS = {
  PUBLIC: 'public',
  AUTH_ONLY: 'auth-only',
};

export const ROUTE_LAYOUTS = {
  PUBLIC: 'public',
  PROTECTED: 'protected',
};
