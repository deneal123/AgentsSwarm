import React, { Suspense } from 'react';
import { Navigate, createBrowserRouter, RouterProvider } from 'react-router-dom';
import { Center, Spinner } from '@chakra-ui/react';
import { ErrorBoundary } from '@shared/ui/molecules';
import { useRoutePreload } from './hooks/useRoutePreload';
import { APP_ROUTES, FALLBACK_ROUTE, ROUTE_CONFIG, RoutePages } from './app/router';
import { AuthOnlyRoute, FeatureFlagRoute, GuestOnlyRoute, PublicRoute, ROUTE_GUARDS, ROUTE_LAYOUTS, layoutMap } from './app/router';

function RouteSuspenseBoundary({ children }) {
  return <Suspense fallback={<Center h="100vh"><Spinner size="lg" /></Center>}>{children}</Suspense>;
}

const guardMap = {
  [ROUTE_GUARDS.PUBLIC]: PublicRoute,
  [ROUTE_GUARDS.AUTH_ONLY]: AuthOnlyRoute,
  [ROUTE_GUARDS.GUEST_ONLY]: GuestOnlyRoute,
  [ROUTE_GUARDS.FEATURE_FLAG]: FeatureFlagRoute,
};

const childRoutesByLayout = ROUTE_CONFIG.reduce((acc, route) => {
  const Guard = guardMap[route.guard] ?? React.Fragment;
  const routeElement = route.redirectTo
    ? <Guard><Navigate to={route.redirectTo} replace /></Guard>
    : (() => {
      const PageComponent = RoutePages[route.page];
      return <Guard><RouteSuspenseBoundary><PageComponent /></RouteSuspenseBoundary></Guard>;
    })();

  acc[route.layout].push({
    ...(route.path === APP_ROUTES.ROOT ? { index: true } : { path: route.path.replace(/^\//, '') }),
    element: routeElement,
  });
  return acc;
}, { [ROUTE_LAYOUTS.PUBLIC]: [], [ROUTE_LAYOUTS.PROTECTED]: [] });

const router = createBrowserRouter([
  { path: '/', element: layoutMap[ROUTE_LAYOUTS.PUBLIC], children: childRoutesByLayout[ROUTE_LAYOUTS.PUBLIC] },
  { path: '/', element: layoutMap[ROUTE_LAYOUTS.PROTECTED], children: childRoutesByLayout[ROUTE_LAYOUTS.PROTECTED] },
  { path: FALLBACK_ROUTE.path, element: <RouteSuspenseBoundary><RoutePages[FALLBACK_ROUTE.page] /></RouteSuspenseBoundary> },
]);

function App() {
  useRoutePreload();
  return <ErrorBoundary level="page"><RouterProvider router={router} /></ErrorBoundary>;
}

export default App;
