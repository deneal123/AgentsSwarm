import React, { Suspense, useEffect } from "react";
import { createBrowserRouter, Navigate, Outlet, RouterProvider, useLocation } from "react-router-dom";
import { Center, Spinner } from "@chakra-ui/react";
import { PublicLayout, ProtectedLayout } from "@shared/ui/layout";
import { ErrorBoundary } from "@shared/ui/molecules";
import { preloadCriticalRoutes } from "./hooks/useRoutePreload";
import { ROUTE_CONFIG, ROUTE_GUARDS, ROUTE_LAYOUTS, RoutePages } from "./routes/routeConfig";
import { useAuth } from "./context/AuthContext";

function RouteSuspenseBoundary({ children }) {
  return (
    <Suspense
      fallback={
        <Center h="100vh">
          <Spinner size="lg" />
        </Center>
      }
    >
      {children}
    </Suspense>
  );
}

function GuardedRoute({ guard, children }) {
  const { isSessionLoading, resolveGuardRedirect } = useAuth();
  const location = useLocation();

  if (isSessionLoading && guard === ROUTE_GUARDS.AUTH_ONLY) {
    return (
      <Center h="100vh">
        <Spinner size="lg" />
      </Center>
    );
  }

  const redirect = resolveGuardRedirect(guard, location);
  if (redirect) {
    return <Navigate to={redirect.to} replace state={redirect.state} />;
  }

  return children;
}

const layoutMap = {
  [ROUTE_LAYOUTS.PUBLIC]: <PublicLayout />,
  [ROUTE_LAYOUTS.PROTECTED]: <ProtectedLayout />,
};

const childRoutesByLayout = ROUTE_CONFIG.filter((route) => route.path !== "*").reduce((acc, route) => {
  const PageComponent = RoutePages[route.page];
  const path = route.path === "/" ? undefined : route.path.replace(/^\//, "");
  const childRoute = {
    ...(route.path === "/" ? { index: true } : { path }),
    element: (
      <GuardedRoute guard={route.guard}>
        <RouteSuspenseBoundary>
          <PageComponent />
        </RouteSuspenseBoundary>
      </GuardedRoute>
    ),
  };
  acc[route.layout].push(childRoute);
  return acc;
}, { [ROUTE_LAYOUTS.PUBLIC]: [], [ROUTE_LAYOUTS.PROTECTED]: [] });

const router = createBrowserRouter([
  {
    path: "/",
    element: layoutMap[ROUTE_LAYOUTS.PUBLIC],
    children: childRoutesByLayout[ROUTE_LAYOUTS.PUBLIC],
  },
  {
    path: "/",
    element: layoutMap[ROUTE_LAYOUTS.PROTECTED],
    children: childRoutesByLayout[ROUTE_LAYOUTS.PROTECTED],
  },
  {
    path: "*",
    element: (
      <RouteSuspenseBoundary>
        <RoutePages.NotFoundPage />
      </RouteSuspenseBoundary>
    ),
  },
]);

function App() {
  useEffect(() => {
    preloadCriticalRoutes();
  }, []);

  return (
    <ErrorBoundary level="page">
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}

export default App;
