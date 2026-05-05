/**
 * useResponsive — хук для адаптивного дизайна
 * Предоставляет информацию о текущем размере экрана и breakpoints
 */

import { useState, useEffect, useMemo, useCallback } from "react";
import { useBreakpointValue } from "@chakra-ui/react";

// Breakpoints согласно Chakra UI (можно настроить)
export const BREAKPOINTS = {
  base: 0,
  sm: 480,
  md: 768,
  lg: 992,
  xl: 1280,
  "2xl": 1536,
};

/**
 * Хук для определения текущего breakpoint
 * @returns {Object} Объект с информацией о текущем breakpoint
 */
export function useResponsive() {
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== "undefined" ? window.innerWidth : 0,
    height: typeof window !== "undefined" ? window.innerHeight : 0,
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    let timeoutId = null;

    const handleResize = () => {
      // Debounce для производительности
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      timeoutId = setTimeout(() => {
        setWindowSize({
          width: window.innerWidth,
          height: window.innerHeight,
        });
      }, 100);
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, []);

  const breakpoint = useMemo(() => {
    const { width } = windowSize;
    if (width >= BREAKPOINTS["2xl"]) return "2xl";
    if (width >= BREAKPOINTS.xl) return "xl";
    if (width >= BREAKPOINTS.lg) return "lg";
    if (width >= BREAKPOINTS.md) return "md";
    if (width >= BREAKPOINTS.sm) return "sm";
    return "base";
  }, [windowSize]);

  const isMobile = useMemo(() => windowSize.width < BREAKPOINTS.md, [windowSize.width]);

  const isTablet = useMemo(
    () => windowSize.width >= BREAKPOINTS.md && windowSize.width < BREAKPOINTS.lg,
    [windowSize.width],
  );

  const isDesktop = useMemo(() => windowSize.width >= BREAKPOINTS.lg, [windowSize.width]);

  const isLandscape = useMemo(() => windowSize.width > windowSize.height, [windowSize]);

  return {
    windowSize,
    breakpoint,
    isMobile,
    isTablet,
    isDesktop,
    isLandscape,
    // Утилитарные функции
    isBreakpoint: useCallback((bp) => breakpoint === bp, [breakpoint]),
    isBreakpointUp: useCallback((bp) => windowSize.width >= BREAKPOINTS[bp], [windowSize.width]),
    isBreakpointDown: useCallback((bp) => windowSize.width < BREAKPOINTS[bp], [windowSize.width]),
  };
}

/**
 * Хук для адаптивных значений с Chakra UI
 * @param {Object} values - Объект со значениями для разных breakpoints
 * @returns {*} Текущее значение для активного breakpoint
 *
 * @example
 * const columns = useResponsiveValue({ base: 1, md: 2, lg: 3 });
 */
export function useResponsiveValue(values) {
  return useBreakpointValue(values);
}

/**
 * Хук для определения touch-устройства
 * @returns {boolean} true если устройство поддерживает touch
 */
export function useIsTouchDevice() {
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const checkTouch = () => {
      setIsTouch(
        "ontouchstart" in window ||
          navigator.maxTouchPoints > 0 ||
          window.matchMedia("(pointer: coarse)").matches,
      );
    };

    checkTouch();

    // Слушаем изменения (например, при подключении мыши к планшету)
    const mediaQuery = window.matchMedia("(pointer: coarse)");
    const handler = () => checkTouch();

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handler);
    } else {
      // Fallback для старых браузеров
      mediaQuery.addListener(handler);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener("change", handler);
      } else {
        mediaQuery.removeListener(handler);
      }
    };
  }, []);

  return isTouch;
}

/**
 * Хук для определения prefers-reduced-motion
 * @returns {boolean} true если пользователь предпочитает уменьшенную анимацию
 */
export function usePrefersReducedMotion() {
  const [prefersReduced, setPrefersReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReduced(mediaQuery.matches);

    const handler = (event) => setPrefersReduced(event.matches);

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handler);
    } else {
      mediaQuery.addListener(handler);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener("change", handler);
      } else {
        mediaQuery.removeListener(handler);
      }
    };
  }, []);

  return prefersReduced;
}

/**
 * Хук для ленивой загрузки контента при скролле (Intersection Observer)
 * @param {Object} options - Опции IntersectionObserver
 * @returns {[Function, boolean]} [ref callback, isVisible]
 */
export function useInView(options = {}) {
  const [isInView, setIsInView] = useState(false);
  const [element, setElement] = useState(null);

  useEffect(() => {
    if (!element || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          // Отключаем наблюдение после первого появления (lazy load)
          if (options.triggerOnce !== false) {
            observer.disconnect();
          }
        } else if (options.triggerOnce === false) {
          setIsInView(false);
        }
      },
      {
        threshold: options.threshold || 0,
        rootMargin: options.rootMargin || "50px",
        ...options,
      },
    );

    observer.observe(element);

    return () => observer.disconnect();
  }, [element, options]);

  return [setElement, isInView];
}

export default useResponsive;
