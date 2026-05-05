import { useCallback, useEffect, useState } from 'react';
import { COMPOSER_MAX_HEIGHT_PX, COMPOSER_MIN_HEIGHT_PX } from '../constants/limits';

export const useComposerAutosize = ({ inputRef, value }) => {
  const [composerHeightPx, setComposerHeightPx] = useState(COMPOSER_MIN_HEIGHT_PX);

  const recalcComposerHeight = useCallback(() => {
    const el = inputRef.current;
    if (!el) {
      return;
    }
    el.style.height = 'auto';
    const next = Math.min(COMPOSER_MAX_HEIGHT_PX, Math.max(COMPOSER_MIN_HEIGHT_PX, el.scrollHeight));
    setComposerHeightPx(next);
    el.style.height = `${next}px`;
  }, [inputRef]);

  useEffect(() => {
    recalcComposerHeight();
  }, [value, recalcComposerHeight]);

  return {
    composerHeightPx,
    recalcComposerHeight,
  };
};
