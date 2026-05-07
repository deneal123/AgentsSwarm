import { renderHook, act } from '@testing-library/react';
import { useChatStreamingLifecycle } from '@features/chat/hooks/orchestration/useChatStreamingLifecycle';

describe('useChatStreamingLifecycle', () => {
  it('handles lifecycle callbacks', () => {
    const setIsLoading = jest.fn();
    const setError = jest.fn();
    const appendTraceEvent = jest.fn();
    const finalizeTraceSession = jest.fn();
    const setMessages = jest.fn();
    const setInputValue = jest.fn();
    const { result } = renderHook(() => useChatStreamingLifecycle({ setIsLoading, setError, appendTraceEvent, finalizeTraceSession, setMessages, setInputValue }));
    act(() => result.current.actions.onJobCreated({ job_id: 'j1' }));
    expect(setIsLoading).toHaveBeenCalledWith(true);
    act(() => result.current.actions.onError({ message: 'boom' }));
    expect(setError).toHaveBeenCalledWith('boom');
  });
});
