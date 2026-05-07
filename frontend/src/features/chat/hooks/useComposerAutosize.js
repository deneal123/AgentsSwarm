import { useCallback, useEffect, useRef, useState } from 'react';
import { COMPOSER_MAX_HEIGHT_PX, COMPOSER_MIN_HEIGHT_PX } from '../constants/limits';

export const useComposerAutosize = ({ inputRef, value }) => {
  const [composerHeightPx, setComposerHeightPx] = useState(COMPOSER_MIN_HEIGHT_PX);
  const frameRef = useRef(0);

  const recalcComposerHeight = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (frameRef.current) {
      window.cancelAnimationFrame(frameRef.current);
    }
    frameRef.current = window.requestAnimationFrame(() => {
      const el = inputRef.current;
      if (!el) {
        return;
      }
      el.style.height = 'auto';
      const next = Math.min(COMPOSER_MAX_HEIGHT_PX, Math.max(COMPOSER_MIN_HEIGHT_PX, el.scrollHeight));
      setComposerHeightPx((prev) => (prev === next ? prev : next));
      el.style.height = `${next}px`;
    });
  }, [inputRef]);

  useEffect(() => {
    recalcComposerHeight();
  }, [value, recalcComposerHeight]);

  useEffect(() => () => {
    if (typeof window !== 'undefined' && frameRef.current) {
      window.cancelAnimationFrame(frameRef.current);
    }
  }, []);

  return {
    composerHeightPx,
    recalcComposerHeight,
  };
};
