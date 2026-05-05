import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import Cookies from "js-cookie";
import useLocalStorage from "../hooks/useLocalStorage";
import { fetchProfile, logoutLocal } from "@api";
import extractErrorInfo from "@utils/errorHandler";
import { registerUnauthorizedHandler } from "@api/client";

const AuthContext = createContext({
  isAuthenticated: false,
  isSessionLoading: true,
  user: null,
  error: null,
  setAuthenticated: () => {},
  refreshSession: async () => {},
  logout: () => {},
});

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

  useEffect(() => {
    const unregister = registerUnauthorizedHandler(logout);
    return () => {
      unregister?.();
    };
  }, [logout]);

  const value = useMemo(
    () => ({
      isAuthenticated,
      isSessionLoading,
      user,
      error,
      setAuthenticated,
      refreshSession,
      logout,
    }),
    [error, isAuthenticated, isSessionLoading, logout, refreshSession, setAuthenticated, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
