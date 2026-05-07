import { renderHook } from '@testing-library/react';
import { useChatTransport } from '@features/chat/hooks/useChatTransport';

jest.mock('@features/chat/model/useWebSocketChat', () => ({
  useWebSocketChat: jest.fn(),
}));

const { useWebSocketChat } = require('@features/chat/model/useWebSocketChat');

describe('useChatTransport websocket edge cases', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('injects safe onMessage callback when callbacks are undefined', () => {
    useWebSocketChat.mockReturnValue({
      isConnected: false,
      connectionState: 'disconnected',
      currentJob: null,
      agentStatus: 'idle',
      sendMessage: jest.fn(),
      cancelJob: jest.fn(),
    });

    renderHook(() => useChatTransport({ threadId: 'thread-1', callbacks: undefined, isAuthenticated: false }));

    expect(useWebSocketChat).toHaveBeenCalledWith(
      'thread-1',
      expect.objectContaining({
        onMessage: expect.any(Function),
      }),
      false,
    );
  });

  it('keeps websocket transport disabled while reconnecting', () => {
    useWebSocketChat.mockReturnValue({
      isConnected: true,
      connectionState: 'reconnecting',
      currentJob: null,
      agentStatus: 'reconnecting',
      sendMessage: jest.fn(),
      cancelJob: jest.fn(),
    });

    const { result } = renderHook(() => useChatTransport({ threadId: 'thread-2', callbacks: {}, isAuthenticated: true }));

    expect(result.current.useWebSocket).toBe(false);
  });

  it('keeps websocket transport disabled when connected flag is stale false', () => {
    useWebSocketChat.mockReturnValue({
      isConnected: false,
      connectionState: 'connected',
      currentJob: { id: 'job-1' },
      agentStatus: 'streaming',
      sendMessage: jest.fn(),
      cancelJob: jest.fn(),
    });

    const { result } = renderHook(() => useChatTransport({ threadId: 'thread-3', callbacks: {}, isAuthenticated: true }));

    expect(result.current.useWebSocket).toBe(false);
    expect(result.current.currentJob).toEqual({ id: 'job-1' });
  });

  it('enables websocket transport only when fully connected', () => {
    useWebSocketChat.mockReturnValue({
      isConnected: true,
      connectionState: 'connected',
      currentJob: null,
      agentStatus: 'idle',
      sendMessage: jest.fn(),
      cancelJob: jest.fn(),
    });

    const { result } = renderHook(() => useChatTransport({ threadId: 'thread-4', callbacks: {}, isAuthenticated: true }));

    expect(result.current.useWebSocket).toBe(true);
  });
});
