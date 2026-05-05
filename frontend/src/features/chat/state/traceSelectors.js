export const selectActiveTraceSession = (state) => {
  return state.sessions.find((session) => session.id === state.activeSessionId) || null;
};

export const selectTraceSessionById = (state, sessionId) => {
  return state.sessions.find((session) => session.id === sessionId) || null;
};

export const selectTraceSessionByAnchor = (state) => {
  const grouped = new Map();
  state.sessions.forEach((session) => {
    const key = session?.anchorMessageId;
    if (!key) {
      return;
    }
    const prev = grouped.get(key);
    if (!prev) {
      grouped.set(key, session);
      return;
    }
    const prevTs = new Date(prev.startedAt || 0).getTime();
    const curTs = new Date(session.startedAt || 0).getTime();
    if (curTs >= prevTs) {
      grouped.set(key, session);
    }
  });
  return grouped;
};
