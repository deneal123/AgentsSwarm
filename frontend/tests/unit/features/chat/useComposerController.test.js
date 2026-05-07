import { renderHook, act } from '@testing-library/react';
import { useComposerController } from '../../../../src/features/chat/hooks/useComposerController';

describe('useComposerController', () => {
  test('submits with Enter and clears value', () => {
    const onSubmit = jest.fn();
    const { result } = renderHook(() => useComposerController({ onSubmit, onCancelSubmit: jest.fn(), disabled: false }));

    act(() => result.current.onChange('hello'));

    const event = { key: 'Enter', shiftKey: false, preventDefault: jest.fn() };
    act(() => result.current.onKeyDown(event));

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onSubmit).toHaveBeenCalledWith('hello');
    expect(result.current.value).toBe('');
  });

  test('does not submit with Shift+Enter', () => {
    const onSubmit = jest.fn();
    const { result } = renderHook(() => useComposerController({ onSubmit, onCancelSubmit: jest.fn(), disabled: false }));

    act(() => result.current.onChange('hello'));
    const event = { key: 'Enter', shiftKey: true, preventDefault: jest.fn() };
    act(() => result.current.onKeyDown(event));

    expect(onSubmit).not.toHaveBeenCalled();
  });

  test('calls cancel on Escape while disabled', () => {
    const onCancelSubmit = jest.fn();
    const { result } = renderHook(() => useComposerController({ onSubmit: jest.fn(), onCancelSubmit, disabled: true }));
    const event = { key: 'Escape', preventDefault: jest.fn() };

    act(() => result.current.onKeyDown(event));

    expect(onCancelSubmit).toHaveBeenCalled();
  });
});
