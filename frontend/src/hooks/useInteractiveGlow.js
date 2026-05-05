import { useCallback, useEffect, useMemo, useRef } from "react";

const DEFAULT_POSITION = { x: 50, y: 50 };

const clampPercent = (value) => {
  if (Number.isNaN(value)) return 50;
  return Math.max(0, Math.min(100, value));
};

/**
 * useInteractiveGlow — хук для управления css-переменными свечения без React setState.
 * Возвращает ref, стили и обработчики, которые можно повесить на контейнер.
 */
export function useInteractiveGlow({ disabled = false, initial = DEFAULT_POSITION } = {}) {
  // Full animations - ignore reduced motion preference
  const isMotionDisabled = disabled;
  const nodeRef = useRef(null);
  const frameRef = useRef(null);

  const setGlowPosition = useCallback(
    (x = initial.x, y = initial.y) => {
      const node = nodeRef.current;
      if (!node) return;
      node.style.setProperty("--glow-x", `${clampPercent(x)}%`);
      node.style.setProperty("--glow-y", `${clampPercent(y)}%`);
    },
    [initial.x, initial.y],
  );

  const resetGlowPosition = useCallback(() => {
    setGlowPosition(initial.x, initial.y);
  }, [initial.x, initial.y, setGlowPosition]);

  const handleMouseMove = useCallback(
    (event) => {
      if (isMotionDisabled) return;
      const target = nodeRef.current ?? event.currentTarget;
      if (!target) return;
      const rect = target.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 100;
      const y = ((event.clientY - rect.top) / rect.height) * 100;
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
      frameRef.current = window.requestAnimationFrame(() => setGlowPosition(x, y));
    },
    [isMotionDisabled, setGlowPosition],
  );

  const handleMouseLeave = useCallback(() => {
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
    resetGlowPosition();
  }, [resetGlowPosition]);

  useEffect(() => {
    resetGlowPosition();
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [resetGlowPosition]);

  useEffect(() => {
    if (isMotionDisabled) {
      resetGlowPosition();
    }
  }, [isMotionDisabled, resetGlowPosition]);

  const glowStyle = useMemo(
    () => ({
      "--glow-x": `${initial.x}%`,
      "--glow-y": `${initial.y}%`,
    }),
    [initial.x, initial.y],
  );

  return {
    glowRef: nodeRef,
    glowStyle,
    onGlowMouseMove: isMotionDisabled ? undefined : handleMouseMove,
    onGlowMouseLeave: isMotionDisabled ? undefined : handleMouseLeave,
  };
}

export default useInteractiveGlow;
