import { renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useChatInitialization } from '@features/chat/hooks/orchestration/useChatInitialization';

describe('useChatInitialization', () => {
  it('builds thread and params contract', () => {
    const wrapper = ({ children }) => <MemoryRouter initialEntries={['/chat?model=gpt&initial=hello']}>{children}</MemoryRouter>;
    const { result } = renderHook(() => useChatInitialization('t1'), { wrapper });
    expect(result.current.state.threadId).toBe('t1');
    expect(result.current.state.initialMessage).toBe('hello');
    expect(result.current.state.selectedModelOverride).toBe('gpt');
  });
});
