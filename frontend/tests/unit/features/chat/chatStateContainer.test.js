import { CHAT_ACTIONS, chatStateReducer, initialChatState } from '@features/chat/model/chatStateContainer';

describe('chatStateContainer transitions', () => {
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
});
