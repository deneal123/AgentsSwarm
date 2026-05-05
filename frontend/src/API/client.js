import axios from "axios";

const resolveApiBaseUrl = () => {
  const envApiBase = (import.meta.env?.REACT_APP_API_BASE_URL || process.env?.REACT_APP_API_BASE_URL);
  if (envApiBase) {
    return envApiBase;
  }

  if (typeof window !== "undefined") {
    const isLocalHost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocalHost) {
      return "http://localhost:8000";
    }
  }

  return "/";
};

const API_BASE_URL = resolveApiBaseUrl();

let unauthorizedHandler = null;

// Публичные эндпоинты, для которых не требуется авторизация
const PUBLIC_ENDPOINTS = [
  "/api/health",
  "/api/chats/",
  "/api/chats/*/message"
];

export const registerUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) {
      unauthorizedHandler = null;
    }
  };
};

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Проверяем, является ли запрос публичным эндпоинтом
      const requestUrl = error.config?.url || "";
      const isPublicEndpoint = PUBLIC_ENDPOINTS.some((endpoint) => requestUrl.includes(endpoint));

      // Вызываем unauthorizedHandler только для защищённых эндпоинтов
      if (!isPublicEndpoint && typeof unauthorizedHandler === "function") {
        unauthorizedHandler();
      }
    }
    return Promise.reject(error);
  },
);

export default client;
