import React, { Suspense } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { Center, Spinner } from '@chakra-ui/react';
import { ErrorBoundary } from '@shared/ui/molecules';
import { useRoutePreload } from './hooks/useRoutePreload';
import { ROUTE_CONFIG, RoutePages } from './routes/routeConfig';
import { AuthOnlyRoute, PublicRoute, ROUTE_GUARDS, ROUTE_LAYOUTS, layoutMap } from './app/router';

function RouteSuspenseBoundary({ children }) {
  return <Suspense fallback={<Center h="100vh"><Spinner size="lg" /></Center>}>{children}</Suspense>;
}

const guardMap = {
  [ROUTE_GUARDS.PUBLIC]: PublicRoute,
  [ROUTE_GUARDS.AUTH_ONLY]: AuthOnlyRoute,
};

const childRoutesByLayout = ROUTE_CONFIG.filter((route) => route.path !== '*').reduce((acc, route) => {
  const PageComponent = RoutePages[route.page];
  const Guard = guardMap[route.guard] ?? React.Fragment;
  acc[route.layout].push({
    ...(route.path === '/' ? { index: true } : { path: route.path.replace(/^\//, '') }),
    element: <Guard><RouteSuspenseBoundary><PageComponent /></RouteSuspenseBoundary></Guard>,
  });
  return acc;
}, { [ROUTE_LAYOUTS.PUBLIC]: [], [ROUTE_LAYOUTS.PROTECTED]: [] });

const router = createBrowserRouter([
  { path: '/', element: layoutMap[ROUTE_LAYOUTS.PUBLIC], children: childRoutesByLayout[ROUTE_LAYOUTS.PUBLIC] },
  { path: '/', element: layoutMap[ROUTE_LAYOUTS.PROTECTED], children: childRoutesByLayout[ROUTE_LAYOUTS.PROTECTED] },
  { path: '*', element: <RouteSuspenseBoundary><RoutePages.NotFoundPage /></RouteSuspenseBoundary> },
]);

function App() {
  useRoutePreload();
  return <ErrorBoundary level="page"><RouterProvider router={router} /></ErrorBoundary>;
}

export default App;
