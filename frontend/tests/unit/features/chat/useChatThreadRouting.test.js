import { renderHook } from '@testing-library/react';
import { useChatThreadRouting } from '@features/chat/hooks/orchestration/useChatThreadRouting';

describe('useChatThreadRouting', () => {
  it('redirects to fallback thread when route missing', () => {
    const navigate = jest.fn();
    renderHook(() => useChatThreadRouting({ routeThreadId: '', initialMessage: '', threadId: 't2', navigate }));
    expect(navigate).toHaveBeenCalledWith('/chat/t2', { replace: true });
  });
});
