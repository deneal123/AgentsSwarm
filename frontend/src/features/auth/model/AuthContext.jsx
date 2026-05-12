import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import Cookies from "js-cookie";
import useLocalStorage from "@hooks/useLocalStorage";
import { fetchProfile, logoutLocal } from "@api";
import extractErrorInfo from "@utils/errorHandler";
import { registerUnauthorizedHandler } from "@api/httpClient";
import { APP_ROUTES } from "@app/router";

const AuthSessionContext = createContext(null);
const AuthActionsContext = createContext(null);

export function AuthProvider({ children }) {
  const [storedAuth, setStoredAuth] = useLocalStorage("telerag:isAuthenticated", false);
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(storedAuth));
  const [user, setUser] = useState(null);
  const [isSessionLoading, setIsSessionLoading] = useState(true);
  const [error, setError] = useState(null);

  const setAuthenticated = useCallback(
    (state, nextUser = null) => {
      setIsAuthenticated(state);
      setStoredAuth(state);
      setUser(state ? nextUser : null);
    },
    [setStoredAuth],
  );

  const clearSession = useCallback(() => {
    setAuthenticated(false, null);
    setError(null);
  }, [setAuthenticated]);

  const refreshSession = useCallback(async () => {
    setIsSessionLoading(true);
    setError(null);
    try {
      const profile = await fetchProfile();
      setAuthenticated(true, profile);
      return profile;
    } catch (err) {
      const isUnauthorized = err?.response?.status === 401;
      if (!isUnauthorized) {
        const { userMessage } = extractErrorInfo(err, {
          fallbackMessage: "Не удалось восстановить сессию",
        });
        setError(userMessage);
      }
      clearSession();
      throw err;
    } finally {
      setIsSessionLoading(false);
    }
  }, [clearSession, setAuthenticated]);

  useEffect(() => {
    refreshSession().catch(() => {});
  }, [refreshSession]);

  const logout = useCallback(() => {
    logoutLocal();
    Cookies.remove("beautiful_cookie");
    clearSession();
  }, [clearSession]);

  const resolveGuardRedirect = useCallback(
    (guardType, location) => {
      if (isSessionLoading) {
        return null;
      }
      if (guardType === "auth-only" && !isAuthenticated) {
        return {
          to: APP_ROUTES.LOGIN,
          state: { from: location },
        };
      }
      if (guardType === "guest-only" && isAuthenticated) {
        return {
          to: APP_ROUTES.ROOT,
        };
      }
      if (guardType === "feature-flag") {
        return {
          to: APP_ROUTES.ROOT,
        };
      }
      return null;
    },
    [isAuthenticated, isSessionLoading],
  );

  useEffect(() => {
    const unregister = registerUnauthorizedHandler(logout);
    return () => {
      unregister?.();
    };
  }, [logout]);

  const sessionValue = useMemo(
    () => ({ isAuthenticated, isSessionLoading, user, error }),
    [error, isAuthenticated, isSessionLoading, user],
  );

  const actionsValue = useMemo(
    () => ({ setAuthenticated, refreshSession, logout, resolveGuardRedirect }),
    [logout, refreshSession, resolveGuardRedirect, setAuthenticated],
  );

  return (
    <AuthSessionContext.Provider value={sessionValue}>
      <AuthActionsContext.Provider value={actionsValue}>{children}</AuthActionsContext.Provider>
    </AuthSessionContext.Provider>
  );
}

export function useAuthSession() {
  return useContext(AuthSessionContext);
}

export function useAuthActions() {
  return useContext(AuthActionsContext);
}

export function useAuth() {
  const session = useAuthSession();
  const actions = useAuthActions();
  return useMemo(() => ({ ...session, ...actions }), [actions, session]);
}
