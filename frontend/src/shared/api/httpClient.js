import axios from 'axios';
import { mapApiError } from './dtoMappers';

const resolveApiBaseUrl = () => {
  const envApiBase = import.meta.env?.REACT_APP_API_BASE_URL || process.env?.REACT_APP_API_BASE_URL;
  if (envApiBase) return envApiBase;
  if (typeof window !== 'undefined') {
    const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocalHost) return 'http://localhost:8000';
  }
  return '/';
};

const DEFAULT_TIMEOUT_MS = 30000;
const RETRY_CONFIG = { retries: 2, retryDelayMs: 400 };
const PUBLIC_ENDPOINTS = ['/api/health', '/api/chats/', '/api/chats/*/message'];

let unauthorizedHandler = null;
let refreshTokenHandler = null;
let refreshRequest = null;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const isPublicEndpoint = (requestUrl = '') => PUBLIC_ENDPOINTS.some((endpoint) => requestUrl.includes(endpoint));
const isRetryableStatus = (status) => !status || status >= 500 || status === 429;

export const registerUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
};

export const registerRefreshTokenHandler = (handler) => {
  refreshTokenHandler = handler;
  return () => {
    if (refreshTokenHandler === handler) refreshTokenHandler = null;
  };
};

const httpClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  withCredentials: true,
  timeout: DEFAULT_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

httpClient.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('auth_token') : null;
  const headers = { ...(config.headers || {}) };
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }
  return {
    ...config,
    headers,
    timeout: config.timeout ?? DEFAULT_TIMEOUT_MS,
  };
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {};
    const status = error.response?.status;

    if (axios.isCancel(error)) {
      return Promise.reject(mapApiError(error, { kind: 'canceled' }));
    }

    if (status === 401 && !config.__isRetryAfterRefresh && !isPublicEndpoint(config.url || '') && typeof refreshTokenHandler === 'function') {
      config.__isRetryAfterRefresh = true;
      refreshRequest = refreshRequest || Promise.resolve(refreshTokenHandler());
      try {
        await refreshRequest;
        return httpClient.request(config);
      } catch (refreshError) {
        if (typeof unauthorizedHandler === 'function') unauthorizedHandler();
        return Promise.reject(mapApiError(refreshError));
      } finally {
        refreshRequest = null;
      }
    }

    const retryCount = config.__retryCount || 0;
    if (isRetryableStatus(status) && retryCount < RETRY_CONFIG.retries && !config.__skipRetry) {
      config.__retryCount = retryCount + 1;
      await sleep(RETRY_CONFIG.retryDelayMs * config.__retryCount);
      return httpClient.request(config);
    }

    if (status === 401 && !isPublicEndpoint(config.url || '') && typeof unauthorizedHandler === 'function') {
      unauthorizedHandler();
    }

    return Promise.reject(mapApiError(error));
  },
);

export default httpClient;
