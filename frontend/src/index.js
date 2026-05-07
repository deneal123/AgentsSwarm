// Полифиллы для кроссбраузерной совместимости (должны быть первыми)
import "./utils/polyfills";

import React from "react";
import ReactDOM from "react-dom/client";
import { ChakraProvider, ColorModeScript } from "@chakra-ui/react";
import App from "./App";
import theme from "./theme";
import { AuthProvider } from "./app/providers";
import { reportWebVitals } from "./utils/webVitals";
import "./xy-theme.css";
import {
  registerServiceWorker,
  unregisterServiceWorker,
} from "./serviceWorkerRegistration";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
      <ChakraProvider theme={theme}>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <AuthProvider>
        <App />
      </AuthProvider>
    </ChakraProvider>
);

reportWebVitals({ debug: process.env.NODE_ENV === "development" });

if (process.env.NODE_ENV === "production") {
  registerServiceWorker();
} else {
  unregisterServiceWorker();
}
