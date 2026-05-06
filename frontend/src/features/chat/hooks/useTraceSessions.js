import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TRACE_MAX_ITEMS, TRACE_MAX_SESSIONS } from "../constants/limits";
import { clampTraceDetail } from "../utils/trace";

export function useTraceSessions({ showTracePanel }) {
  const [traceSessions, setTraceSessions] = useState([]);
  const [activeTraceSessionId, setActiveTraceSessionId] = useState(null);
  const [tracePanelsExpanded, setTracePanelsExpanded] = useState({});
  const traceSessionsRef = useRef([]);
  const activeTraceSessionIdRef = useRef(null);

  useEffect(() => {
    traceSessionsRef.current = traceSessions;
  }, [traceSessions]);

  useEffect(() => {
    activeTraceSessionIdRef.current = activeTraceSessionId;
  }, [activeTraceSessionId]);

  const createTraceSession = useCallback((title = "Подготовка запроса", anchorMessageId = null) => {
    const sessionId = `trace_session_${Date.now()}_${Math.random()}`;
    const session = {
      id: sessionId,
      title,
      status: "running",
      startedAt: new Date().toISOString(),
      events: [],
      anchorMessageId,
    };

    setTraceSessions((prev) => [...prev, session].slice(-TRACE_MAX_SESSIONS));
    setTracePanelsExpanded((prev) => ({ ...prev, [sessionId]: true }));
    setActiveTraceSessionId(sessionId);
    activeTraceSessionIdRef.current = sessionId;
    return sessionId;
  }, []);

  const ensureTraceSession = useCallback((fallbackTitle = "Подготовка запроса", anchorMessageId = null) => {
    const activeId = activeTraceSessionIdRef.current;
    const activeSession = traceSessionsRef.current.find((session) => session.id === activeId);
    if (activeSession && activeSession.status === "running") {
      return activeSession.id;
    }
    return createTraceSession(fallbackTitle, anchorMessageId);
  }, [createTraceSession]);

  const startTraceSession = useCallback((queryText, anchorMessageId = null) => {
    const sessionId = ensureTraceSession("Подготовка запроса", anchorMessageId);
    setTraceSessions((prev) => prev.map((session) => (
      session.id === sessionId
        ? {
            ...session,
            title: clampTraceDetail(queryText, 96),
            anchorMessageId: anchorMessageId || session.anchorMessageId || null,
            status: "running",
            finishedAt: null,
          }
        : session
    )));
    activeTraceSessionIdRef.current = sessionId;
    setActiveTraceSessionId(sessionId);
    setTracePanelsExpanded((prev) => ({ ...prev, [sessionId]: true }));
    return sessionId;
  }, [ensureTraceSession]);

  const appendTraceEvent = useCallback((event, sessionIdOverride = null) => {
    const sessionId = sessionIdOverride || ensureTraceSession("Подготовка запроса");
    if (!event?.title) {
      return;
    }
    const normalizedEvent = {
      id: `trace_${Date.now()}_${Math.random()}`,
      timestamp: event.timestamp || new Date().toISOString(),
      kind: event.kind || "info",
      title: String(event.title),
      detail: clampTraceDetail(event.detail),
    };

    setTraceSessions((prev) => prev.map((session) => {
      if (session.id !== sessionId) return session;
      return {
        ...session,
        status: normalizedEvent.kind === "error" ? "error" : session.status,
        events: [...session.events, normalizedEvent].slice(-TRACE_MAX_ITEMS),
      };
    }));
  }, [ensureTraceSession]);

  const finalizeTraceSession = useCallback((status = "done", sessionIdOverride = null) => {
    const sessionId = sessionIdOverride || activeTraceSessionIdRef.current;
    if (!sessionId) return;
    const finalizedAt = new Date().toISOString();
    setTraceSessions((prev) => prev.map((session) => {
      if (session.id !== sessionId) return session;
      const nextStatus = status === "error" ? "error" : (session.status === "error" ? "error" : "done");
      return { ...session, status: nextStatus, finishedAt: session.finishedAt || finalizedAt };
    }));
  }, []);

  const traceSessionByAnchor = useMemo(() => {
    const map = new Map();
    traceSessions.forEach((session) => {
      if (session.anchorMessageId) {
        map.set(session.anchorMessageId, session);
      }
    });
    return map;
  }, [traceSessions]);

  const activeOrLatestTraceSession = useMemo(() => {
    if (!showTracePanel || !traceSessions.length) return null;
    const activeSession = activeTraceSessionId
      ? traceSessions.find((session) => session.id === activeTraceSessionId)
      : null;
    return activeSession || traceSessions[traceSessions.length - 1];
  }, [activeTraceSessionId, showTracePanel, traceSessions]);

  const resetTraceSessions = useCallback(() => {
    traceSessionsRef.current = [];
    activeTraceSessionIdRef.current = null;
    setTraceSessions([]);
    setActiveTraceSessionId(null);
    setTracePanelsExpanded({});
  }, []);

  return {
    traceSessions,
    tracePanelsExpanded,
    setTracePanelsExpanded,
    traceSessionByAnchor,
    activeOrLatestTraceSession,
    startTraceSession,
    appendTraceEvent,
    finalizeTraceSession,
    resetTraceSessions,
  };
}
