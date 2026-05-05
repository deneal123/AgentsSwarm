// Полифиллы для кроссбраузерной совместимости (должны быть первыми)
import "./utils/polyfills";

import React from "react";
import ReactDOM from "react-dom/client";
import { ChakraProvider, ColorModeScript } from "@chakra-ui/react";
import App from "./App";
import theme from "./theme";
import { AuthProvider } from "./context/AuthContext";
import { reportWebVitals } from "./utils/webVitals";
import "./xy-theme.css";
import {
  registerServiceWorker,
  unregisterServiceWorker,
} from "./serviceWorkerRegistration";

// Логирование переменных окружения
console.log('🔧 Frontend Environment Variables:');
console.log('🔧 REACT_APP_API_BASE_URL:', import.meta.env?.REACT_APP_API_BASE_URL || process.env?.REACT_APP_API_BASE_URL);
console.log('🔧 REACT_APP_WS_BASE_URL:', import.meta.env?.REACT_APP_WS_BASE_URL || process.env?.REACT_APP_WS_BASE_URL);
console.log('🔧 NODE_ENV:', process.env?.NODE_ENV);

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  // <React.StrictMode> disabled for WebSocket compatibility in development
  // <React.StrictMode>
    <ChakraProvider theme={theme}>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <AuthProvider>
        <App />
      </AuthProvider>
    </ChakraProvider>
  // </React.StrictMode>,
);

// Мониторинг производительности Web Vitals
reportWebVitals({ debug: process.env.NODE_ENV === "development" });

// Prefetch критичных чанков для ускорения LCP
// Это загрузит home чанк в фоне сразу после основного bundle
import(/* webpackPrefetch: true, webpackChunkName: "home" */ "@pages/home");

// Регистрируем service worker только в production
if (process.env.NODE_ENV === "production") {
  registerServiceWorker();
} else {
  // In dev, remove old SW registrations so localhost never serves stale bundles.
  unregisterServiceWorker();
}
