import axios from 'axios';
import { normalizeDomainError } from '../lib/error';

const resolveApiBaseUrl = () => {
  const envApiBase = import.meta.env?.REACT_APP_API_BASE_URL || process.env?.REACT_APP_API_BASE_URL;
  if (envApiBase) return envApiBase;
  if (typeof window !== 'undefined') {
    const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocalHost) return 'http://localhost:8000';
  }
  return '/';
};

const PUBLIC_ENDPOINTS = ['/api/health', '/api/chats/', '/api/chats/*/message'];
let unauthorizedHandler = null;

export const registerUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
};

const RETRY_CONFIG = { retries: 2, retryDelayMs: 400 };

const httpClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

httpClient.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('auth_token') : null;
  if (token && !config.headers?.Authorization) {
    config.headers = { ...config.headers, Authorization: `Bearer ${token}` };
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {};
    const status = error.response?.status;
    const isRetryable = !status || status >= 500;
    config.__retryCount = config.__retryCount || 0;

    if (isRetryable && config.__retryCount < RETRY_CONFIG.retries) {
      config.__retryCount += 1;
      await new Promise((resolve) => setTimeout(resolve, RETRY_CONFIG.retryDelayMs * config.__retryCount));
      return httpClient.request(config);
    }

    if (status === 401) {
      const requestUrl = error.config?.url || '';
      const isPublicEndpoint = PUBLIC_ENDPOINTS.some((endpoint) => requestUrl.includes(endpoint));
      if (!isPublicEndpoint && typeof unauthorizedHandler === 'function') {
        unauthorizedHandler();
      }
    }
    return Promise.reject(normalizeDomainError(error));
  },
);

export default httpClient;
