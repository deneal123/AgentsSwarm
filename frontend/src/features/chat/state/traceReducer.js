import { TRACE_MAX_ITEMS, TRACE_MAX_SESSIONS } from '../constants/limits';

export const initialTraceState = {
  sessions: [],
  activeSessionId: null,
  expanded: {},
};

const clampSessions = (sessions) => sessions.slice(-TRACE_MAX_SESSIONS);
const clampEvents = (events) => events.slice(-TRACE_MAX_ITEMS);

export const traceReducer = (state, action) => {
  switch (action.type) {
    case 'create_session': {
      const session = action.payload;
      return {
        ...state,
        sessions: clampSessions([...state.sessions, session]),
        activeSessionId: session.id,
        expanded: { ...state.expanded, [session.id]: true },
      };
    }
    case 'update_session': {
      const { sessionId, patch } = action.payload;
      return {
        ...state,
        sessions: state.sessions.map((session) => (session.id === sessionId ? { ...session, ...patch } : session)),
      };
    }
    case 'append_event': {
      const { sessionId, event } = action.payload;
      return {
        ...state,
        sessions: state.sessions.map((session) => {
          if (session.id !== sessionId) {
            return session;
          }
          const status = event.kind === 'error' ? 'error' : session.status;
          return { ...session, status, events: clampEvents([...(session.events || []), event]) };
        }),
      };
    }
    case 'set_expanded': {
      const { sessionId, expanded } = action.payload;
      return { ...state, expanded: { ...state.expanded, [sessionId]: expanded } };
    }
    case 'set_active':
      return { ...state, activeSessionId: action.payload };
    case 'reset':
      return initialTraceState;
    default:
      return state;
  }
};
