import { useMemo, useReducer } from 'react';
import { traceReducer, initialTraceState } from '../state/traceReducer';
import { clampTraceDetail } from '../utils/trace';
import { selectTraceSessionByAnchor } from '../state/traceSelectors';

const createSession = (title, anchorMessageId = null) => ({
  id: `trace_session_${Date.now()}_${Math.random()}`,
  title: clampTraceDetail(title, 96),
  anchorMessageId,
  status: 'running',
  startedAt: new Date().toISOString(),
  finishedAt: null,
  events: [],
});

export const useTracePanel = () => {
  const [traceState, dispatch] = useReducer(traceReducer, initialTraceState);

  const createTraceSession = (title = 'Подготовка запроса', anchorMessageId = null) => {
    const session = createSession(title, anchorMessageId);
    dispatch({ type: 'create_session', payload: session });
    return session.id;
  };

  const ensureTraceSession = (fallbackTitle = 'Подготовка запроса', anchorMessageId = null) => {
    const current = traceState.sessions.find((session) => session.id === traceState.activeSessionId);
    if (current && current.status === 'running') {
      return current.id;
    }
    return createTraceSession(fallbackTitle, anchorMessageId);
  };

  const startTraceSession = (queryText, anchorMessageId = null) => {
    const sessionId = ensureTraceSession('Подготовка запроса', anchorMessageId);
    dispatch({
      type: 'update_session',
      payload: {
        sessionId,
        patch: {
          title: clampTraceDetail(queryText, 96),
          anchorMessageId,
          status: 'running',
          finishedAt: null,
        },
      },
    });
    dispatch({ type: 'set_active', payload: sessionId });
    dispatch({ type: 'set_expanded', payload: { sessionId, expanded: true } });
    return sessionId;
  };

  const appendTraceEvent = (event, sessionIdOverride = null) => {
    if (!event?.title) {
      return;
    }
    const sessionId = sessionIdOverride || ensureTraceSession('Подготовка запроса');
    const normalizedEvent = {
      id: `trace_${Date.now()}_${Math.random()}`,
      title: String(event.title),
      detail: clampTraceDetail(event.detail),
      kind: event.kind || 'info',
      timestamp: event.timestamp || new Date().toISOString(),
    };
    dispatch({ type: 'append_event', payload: { sessionId, event: normalizedEvent } });
  };

  const finalizeTraceSession = (status = 'done', sessionIdOverride = null) => {
    const sessionId = sessionIdOverride || traceState.activeSessionId;
    if (!sessionId) {
      return;
    }
    dispatch({
      type: 'update_session',
      payload: {
        sessionId,
        patch: {
          status,
          finishedAt: new Date().toISOString(),
        },
      },
    });
  };

  const traceSessionByAnchor = useMemo(() => selectTraceSessionByAnchor(traceState), [traceState]);

  return {
    traceSessions: traceState.sessions,
    activeTraceSessionId: traceState.activeSessionId,
    tracePanelsExpanded: traceState.expanded,
    traceSessionByAnchor,
    createTraceSession,
    startTraceSession,
    appendTraceEvent,
    finalizeTraceSession,
    setTracePanelExpanded: (sessionId, expanded) => dispatch({ type: 'set_expanded', payload: { sessionId, expanded } }),
    setActiveTraceSessionId: (sessionId) => dispatch({ type: 'set_active', payload: sessionId }),
    resetTraceState: () => dispatch({ type: 'reset' }),
  };
};
