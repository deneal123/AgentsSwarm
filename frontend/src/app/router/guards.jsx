import React from 'react';
import { Center, Spinner } from '@chakra-ui/react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@app/providers';
import { ROUTE_GUARDS } from './routes';

function RouteGuard({ children, guard }) {
  const { isSessionLoading, resolveGuardRedirect } = useAuth();
  const location = useLocation();

  if (isSessionLoading) {
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

export function AuthOnlyRoute({ children }) {
  return <RouteGuard guard={ROUTE_GUARDS.AUTH_ONLY}>{children}</RouteGuard>;
}

export function GuestOnlyRoute({ children }) {
  return <RouteGuard guard={ROUTE_GUARDS.GUEST_ONLY}>{children}</RouteGuard>;
}

export function PublicRoute({ children }) {
  return <RouteGuard guard={ROUTE_GUARDS.PUBLIC}>{children}</RouteGuard>;
}

export function FeatureFlagRoute({ children }) {
  return <RouteGuard guard={ROUTE_GUARDS.FEATURE_FLAG}>{children}</RouteGuard>;
}
