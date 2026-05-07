import { useCallback, useMemo } from 'react';
import { useComposerState } from './useComposerState';

export function useComposerController({ onSubmit, onCancelSubmit, disabled }) {
  const composer = useComposerState({ onSubmit });

  const handleSubmit = useCallback(() => {
    if (disabled) {
      return;
    }
    const value = composer.inputValue.trim();
    if (!value) {
      return;
    }
    composer.submit();
    composer.setInputValue('');
    composer.inputRef.current?.focus();
  }, [composer, disabled]);

  const handleChange = useCallback((value) => {
    composer.setInputValue(value);
  }, [composer]);

  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
      return;
    }
    if (event.key === 'Escape' && disabled && onCancelSubmit) {
      event.preventDefault();
      onCancelSubmit();
    }
  }, [disabled, handleSubmit, onCancelSubmit]);

  const contract = useMemo(() => ({
    value: composer.inputValue,
    onChange: handleChange,
    onSubmit: handleSubmit,
    disabled,
    attachments: composer.attachedFile,
    recordingState: composer.isRecording,
  }), [composer.attachedFile, composer.inputValue, composer.isRecording, disabled, handleChange, handleSubmit]);

  return {
    ...composer,
    ...contract,
    onKeyDown: handleKeyDown,
  };
}
