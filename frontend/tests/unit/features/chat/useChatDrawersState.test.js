import { renderHook } from '@testing-library/react';
import { useDisclosure } from '@chakra-ui/react';
import { useChatDrawersState } from '@features/chat/hooks/orchestration/useChatDrawersState';

describe('useChatDrawersState', () => {
  it('exposes state and actions contract', () => {
    const { result } = renderHook(() => useChatDrawersState(useDisclosure()));
    expect(result.current.state.memoryFacts).toEqual([]);
    expect(typeof result.current.actions.setMemoryFacts).toBe('function');
  });
});
