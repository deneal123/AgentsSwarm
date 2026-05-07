import { renderHook, act } from '@testing-library/react';
import { useWebSocketChat } from '@features/chat/model/useWebSocketChat';

jest.mock('@chakra-ui/react', () => ({
  useToast: () => jest.fn(),
}));

describe('useWebSocketChat protocol degradation', () => {
  const originalWebSocket = global.WebSocket;
  const sockets = [];

  class MockWebSocket {
    static OPEN = 1;
    static CONNECTING = 0;

    constructor() {
      this.readyState = MockWebSocket.CONNECTING;
      sockets.push(this);
      setTimeout(() => {
        this.readyState = MockWebSocket.OPEN;
        this.onopen?.();
      }, 0);
    }

    close() {}
    send() {}
  }

  beforeEach(() => {
    sockets.length = 0;
    global.WebSocket = MockWebSocket;
  });

  afterAll(() => {
    global.WebSocket = originalWebSocket;
  });

  it('routes invalid contract events into protocol_error channel and keeps ui alive', async () => {
    const onAgentEvent = jest.fn();
    const onJobCreated = jest.fn();

    renderHook(() => useWebSocketChat('thread-1', { onAgentEvent, onJobCreated }, true));

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });

    act(() => {
      sockets[0].onmessage({
        data: JSON.stringify({
          type: 'job_created',
          job_id: 'job-1',
          thread_id: 'thread-1',
          metadata: {},
          data: 'broken payload',
        }),
      });
    });

    expect(onJobCreated).not.toHaveBeenCalled();
    expect(onAgentEvent).toHaveBeenCalledWith(expect.objectContaining({
      type: 'protocol_error',
      event_type: 'job_created',
    }));
  });
});
