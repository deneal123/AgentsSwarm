import { CHAT_ACTIONS, chatStateReducer, initialChatState } from '@features/chat/model/chatStateContainer';

describe('chatStateContainer transitions', () => {
  it('handles trace lifecycle transitions', () => {
    const started = chatStateReducer(initialChatState, {
      type: CHAT_ACTIONS.TRACE_START_SESSION,
      payload: { id: 'trace-1', events: [], status: 'active' },
    });

    expect(started.traceSessions).toHaveLength(1);
    expect(started.activeTraceSessionId).toBe('trace-1');

    const appended = chatStateReducer(started, {
      type: CHAT_ACTIONS.TRACE_APPEND_EVENT,
      payload: { sessionId: 'trace-1', event: { id: 'event-1', type: 'delta' } },
    });

    expect(appended.traceSessions[0].events).toHaveLength(1);

    const finalized = chatStateReducer(appended, {
      type: CHAT_ACTIONS.TRACE_FINALIZE_SESSION,
      payload: { sessionId: 'trace-1', status: 'completed' },
    });

    expect(finalized.traceSessions[0].status).toBe('completed');
  });

  it('resets traces and preserves non-trace state', () => {
    const prev = {
      ...initialChatState,
      traceSessions: [{ id: 'trace-1', events: [{ id: 'e1' }] }],
      activeTraceSessionId: 'trace-1',
      messages: [{ id: 'm1', content: 'persist' }],
    };

    const next = chatStateReducer(prev, { type: CHAT_ACTIONS.TRACE_RESET });

    expect(next.traceSessions).toEqual([]);
    expect(next.activeTraceSessionId).toBeNull();
    expect(next.messages).toEqual([{ id: 'm1', content: 'persist' }]);
  });

  it('handles socket error transition', () => {
    const prev = { ...initialChatState, loading: true, connectionState: 'connected' };
    const next = chatStateReducer(prev, { type: CHAT_ACTIONS.SOCKET_ERROR, payload: 'boom' });
    expect(next.loading).toBe(false);
    expect(next.connectionState).toBe('error');
    expect(next.error).toBe('boom');
  });

  it('handles reconnect transition', () => {
    const next = chatStateReducer(initialChatState, { type: CHAT_ACTIONS.RECONNECT });
    expect(next.connectionState).toBe('reconnecting');
    expect(next.reconnectAttempts).toBe(1);
  });

  it('handles generation cancellation', () => {
    const prev = { ...initialChatState, loading: true, currentJob: { id: 'job1' } };
    const next = chatStateReducer(prev, { type: CHAT_ACTIONS.CANCEL_GENERATION });
    expect(next.loading).toBe(false);
    expect(next.currentJob).toBeNull();
  });

  it('clears thread state', () => {
    const prev = {
      ...initialChatState,
      messages: [{ id: 'm1' }],
      traceSessions: [{ id: 't1', events: [] }],
      activeTraceSessionId: 't1',
      currentJob: { id: 'job1' },
      error: 'error',
    };
    const next = chatStateReducer(prev, { type: CHAT_ACTIONS.CLEAR_THREAD });
    expect(next.messages).toEqual([]);
    expect(next.traceSessions).toEqual([]);
    expect(next.activeTraceSessionId).toBeNull();
    expect(next.currentJob).toBeNull();
    expect(next.error).toBeNull();
  });

  it('sets default socket error payload when payload is missing', () => {
    const next = chatStateReducer(initialChatState, { type: CHAT_ACTIONS.SOCKET_ERROR });

    expect(next.connectionState).toBe('error');
    expect(next.error).toBe('Socket error');
  });
});
