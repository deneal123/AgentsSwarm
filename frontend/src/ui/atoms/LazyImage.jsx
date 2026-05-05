/**
 * LazyImage — компонент для ленивой загрузки изображений
 * Оптимизирует LCP и CLS метрики
 */

import React, { memo, useState, useCallback } from "react";
import { Box, Image, Skeleton } from "@chakra-ui/react";
import { useInView } from "../hooks/useResponsive";

/**
 * Ленивая загрузка изображений с placeholder и оптимизацией
 * @param {Object} props
 * @param {string} props.src - URL изображения
 * @param {string} props.alt - Alt текст для изображения
 * @param {string} [props.fallbackSrc] - URL fallback изображения
 * @param {string} [props.placeholder] - URL placeholder (blur, низкое качество)
 * @param {number} [props.aspectRatio] - Соотношение сторон для предотвращения CLS
 * @param {Object} [props.sizes] - Responsive sizes для srcSet
 * @param {boolean} [props.priority] - Загружать немедленно (для LCP изображений)
 * @param {Object} props.rest - Остальные props для Image
 */
const LazyImage = memo(function LazyImage({
  src,
  alt,
  fallbackSrc,
  placeholder,
  aspectRatio,
  sizes,
  priority = false,
  objectFit = "cover",
  borderRadius,
  ...rest
}) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [ref, isInView] = useInView({
    rootMargin: "200px", // Preload за 200px до появления
    triggerOnce: true,
  });

  const shouldLoad = priority || isInView;

  const handleLoad = useCallback(() => {
    setIsLoaded(true);
  }, []);

  const handleError = useCallback(() => {
    setHasError(true);
  }, []);

  const imageSrc = hasError && fallbackSrc ? fallbackSrc : src;

  return (
    <Box
      ref={priority ? undefined : ref}
      position="relative"
      overflow="hidden"
      borderRadius={borderRadius}
      // Предотвращение CLS с помощью aspect-ratio
      {...(aspectRatio && {
        sx: {
          aspectRatio: aspectRatio,
        },
      })}
      {...rest}
    >
      {/* Skeleton placeholder */}
      {!isLoaded && (
        <Skeleton
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          startColor="whiteAlpha.50"
          endColor="whiteAlpha.200"
        />
      )}

      {/* Blur placeholder для плавного перехода */}
      {placeholder && !isLoaded && shouldLoad && (
        <Image
          src={placeholder}
          alt=""
          position="absolute"
          top={0}
          left={0}
          width="100%"
          height="100%"
          objectFit={objectFit}
          filter="blur(20px)"
          transform="scale(1.1)"
          aria-hidden="true"
        />
      )}

      {/* Основное изображение */}
      {shouldLoad && (
        <Image
          src={imageSrc}
          alt={alt}
          width="100%"
          height="100%"
          objectFit={objectFit}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          onLoad={handleLoad}
          onError={handleError}
          opacity={isLoaded ? 1 : 0}
          transition="opacity 0.3s ease-in-out"
          // Native lazy loading attributes
          {...(sizes && { sizes })}
        />
      )}
    </Box>
  );
});

/**
 * Компонент для background изображений с ленивой загрузкой
 */
export const LazyBackgroundImage = memo(function LazyBackgroundImage({
  src,
  fallbackSrc,
  children,
  ...rest
}) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [ref, isInView] = useInView({
    rootMargin: "100px",
    triggerOnce: true,
  });

  const imageSrc = hasError && fallbackSrc ? fallbackSrc : src;

  // Preload изображение
  React.useEffect(() => {
    if (!isInView || !imageSrc) return;

    const img = new window.Image();
    img.src = imageSrc;
    img.onload = () => setIsLoaded(true);
    img.onerror = () => setHasError(true);
  }, [isInView, imageSrc]);

  return (
    <Box
      ref={ref}
      backgroundImage={isLoaded ? `url(${imageSrc})` : undefined}
      backgroundSize="cover"
      backgroundPosition="center"
      backgroundRepeat="no-repeat"
      transition="background-image 0.3s ease-in-out"
      {...rest}
    >
      {children}
    </Box>
  );
});

/**
 * Хелпер для генерации srcSet
 * @param {string} baseUrl - Базовый URL изображения
 * @param {number[]} widths - Массив ширин для srcSet
 * @returns {string} srcSet строка
 */
export function generateSrcSet(baseUrl, widths = [320, 640, 960, 1280, 1920]) {
  // Предполагаем, что сервер поддерживает width параметр
  // Адаптировать под конкретный image service
  return widths
    .map((width) => {
      const separator = baseUrl.includes("?") ? "&" : "?";
      return `${baseUrl}${separator}w=${width} ${width}w`;
    })
    .join(", ");
}

/**
 * Хелпер для определения оптимального sizes атрибута
 * @param {Object} options - Опции для разных breakpoints
 * @returns {string} sizes строка
 */
export function generateSizes(options = {}) {
  const defaults = {
    base: "100vw",
    sm: "100vw",
    md: "50vw",
    lg: "33vw",
    xl: "25vw",
  };

  const merged = { ...defaults, ...options };

  const breakpoints = {
    sm: 480,
    md: 768,
    lg: 992,
    xl: 1280,
  };

  const parts = Object.entries(breakpoints)
    .reverse()
    .map(([key, minWidth]) => {
      if (merged[key]) {
        return `(min-width: ${minWidth}px) ${merged[key]}`;
      }
      return null;
    })
    .filter(Boolean);

  parts.push(merged.base);

  return parts.join(", ");
}

export default LazyImage;
