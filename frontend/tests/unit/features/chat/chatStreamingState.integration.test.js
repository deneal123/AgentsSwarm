import { chatStateReducer, initialChatState, CHAT_ACTIONS } from '@features/chat/model/chatStateContainer';

describe('chat streaming state integration', () => {
  it('keeps unified state consistent for job start/chunk/error/complete', () => {
    let state = initialChatState;

    state = chatStateReducer(state, { type: CHAT_ACTIONS.SET_LOADING, payload: true });
    state = chatStateReducer(state, { type: CHAT_ACTIONS.SET_CURRENT_JOB, payload: { id: 'job-1', status: 'processing', progress: 0 } });
    state = chatStateReducer(state, { type: CHAT_ACTIONS.STREAM_APPEND_CHUNK, payload: { chunk: 'Hello', metadata: { source: 'ws' } } });
    state = chatStateReducer(state, { type: CHAT_ACTIONS.STREAM_APPEND_CHUNK, payload: { chunk: ' world', metadata: { source: 'ws' } } });

    expect(state.loading).toBe(true);
    expect(state.currentJob?.id).toBe('job-1');
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0].content).toBe('Hello world');
    expect(state.messages[0].complete).toBe(false);

    state = chatStateReducer(state, { type: CHAT_ACTIONS.SET_ERROR, payload: 'Ошибка чата: boom' });
    expect(state.error).toBe('Ошибка чата: boom');

    state = chatStateReducer(state, { type: CHAT_ACTIONS.STREAM_COMPLETE_LAST_AGENT });
    state = chatStateReducer(state, { type: CHAT_ACTIONS.CLEAR_JOB });
    state = chatStateReducer(state, { type: CHAT_ACTIONS.SET_LOADING, payload: false });

    expect(state.messages[0].complete).toBe(true);
    expect(state.messages[0].isTyping).toBe(false);
    expect(state.currentJob).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBe('Ошибка чата: boom');
  });
});
