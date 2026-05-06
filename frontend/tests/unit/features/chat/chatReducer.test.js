import { chatReducer, CHAT_ACTIONS, initialState } from '@features/chat/context/ChatContext';

describe('chat reducer public behavior', () => {
  it('adds and updates messages', () => {
    const added = chatReducer(initialState, {
      type: CHAT_ACTIONS.ADD_MESSAGE,
      payload: { id: 'm1', content: 'hello' },
    });

    expect(added.messages).toHaveLength(1);

    const updated = chatReducer(added, {
      type: CHAT_ACTIONS.UPDATE_MESSAGE,
      payload: { id: 'm1', content: 'updated' },
    });

    expect(updated.messages[0].content).toBe('updated');
  });

  it('tracks typing users and clears correctly', () => {
    const withTyping = chatReducer(initialState, { type: CHAT_ACTIONS.SET_TYPING, payload: 'u1' });
    expect(withTyping.typingUsers.has('u1')).toBe(true);

    const cleared = chatReducer(withTyping, { type: CHAT_ACTIONS.CLEAR_TYPING, payload: 'u1' });
    expect(cleared.typingUsers.size).toBe(0);
  });

  it('handles job lifecycle', () => {
    const withJob = chatReducer(initialState, {
      type: CHAT_ACTIONS.SET_CURRENT_JOB,
      payload: { id: 'j1', progress: 0 },
    });
    const progressed = chatReducer(withJob, {
      type: CHAT_ACTIONS.UPDATE_JOB_PROGRESS,
      payload: { progress: 70 },
    });

    expect(progressed.currentJob.progress).toBe(70);

    const cleared = chatReducer(progressed, { type: CHAT_ACTIONS.CLEAR_JOB });
    expect(cleared.currentJob).toBeNull();
  });
});
