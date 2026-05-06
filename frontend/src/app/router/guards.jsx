import React from 'react';
import { Center, Spinner } from '@chakra-ui/react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ROUTE_GUARDS } from './routes';

export function AuthOnlyRoute({ children }) {
  const { isSessionLoading, resolveGuardRedirect } = useAuth();
  const location = useLocation();

  if (isSessionLoading) {
    return (
      <Center h="100vh">
        <Spinner size="lg" />
      </Center>
    );
  }

  const redirect = resolveGuardRedirect(ROUTE_GUARDS.AUTH_ONLY, location);
  if (redirect) {
    return <Navigate to={redirect.to} replace state={redirect.state} />;
  }

  return children;
}

export function PublicRoute({ children }) {
  const { resolveGuardRedirect } = useAuth();
  const location = useLocation();
  const redirect = resolveGuardRedirect(ROUTE_GUARDS.PUBLIC, location);

  if (redirect) {
    return <Navigate to={redirect.to} replace state={redirect.state} />;
  }

  return children;
}
