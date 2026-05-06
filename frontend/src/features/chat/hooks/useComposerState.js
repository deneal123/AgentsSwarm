import { useCallback, useRef, useState } from 'react';
import { useComposerAutosize } from './useComposerAutosize';

export function useComposerState({ onSubmit }) {
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const [inputValue, setInputValue] = useState('');
  const [attachedFile, setAttachedFile] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const { composerHeightPx } = useComposerAutosize({ inputRef, value: inputValue });

  const submit = useCallback(() => {
    onSubmit(inputValue);
  }, [inputValue, onSubmit]);

  return {
    inputRef,
    fileInputRef,
    inputValue,
    setInputValue,
    attachedFile,
    setAttachedFile,
    isRecording,
    setIsRecording,
    composerHeightPx,
    submit,
  };
}
