import React, { Suspense, useEffect } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Center, Spinner } from "@chakra-ui/react";
import PublicLayout from "./ui/layout/PublicLayout";
import ErrorBoundary from "./ui/molecules/ErrorBoundary";
import { preloadCriticalRoutes } from "./hooks/useRoutePreload";

import { APP_ROUTE_SEGMENTS, RoutePages } from "./routes/routeConfig";

const router = createBrowserRouter([
  {
    path: "/",
    element: <PublicLayout />,
    children: [
      { index: true, element: <RoutePages.ChatPage /> },
      { path: APP_ROUTE_SEGMENTS.LOGIN, element: <RoutePages.LoginPage /> },
      { path: APP_ROUTE_SEGMENTS.REGISTER, element: <RoutePages.SignUpPage /> },
      { path: APP_ROUTE_SEGMENTS.CHAT_THREAD, element: <RoutePages.ChatPage /> },
    ],
  },
  { path: "*", element: <RoutePages.NotFoundPage /> },
]);

function App() {
  useEffect(() => {
    preloadCriticalRoutes();
  }, []);

  return (
    <ErrorBoundary level="page">
      <Suspense
        fallback={
          <Center h="100vh">
            <Spinner size="lg" />
          </Center>
        }
      >
        <RouterProvider router={router} />
      </Suspense>
    </ErrorBoundary>
  );
}

export default App;
