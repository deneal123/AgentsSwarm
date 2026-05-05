import React, { memo, useRef, useMemo, useCallback } from "react";
import { Box, SimpleGrid, useBreakpointValue } from "@chakra-ui/react";

/**
 * Порог количества элементов, после которого включается виртуализация
 */
const VIRTUALIZATION_THRESHOLD = 20;

/**
 * Количество дополнительных элементов для рендера за пределами viewport
 */
const OVERSCAN = 3;

/**
 * VirtualizedGrid - Компонент для отображения больших списков с виртуализацией
 *
 * Для списков меньше VIRTUALIZATION_THRESHOLD элементов использует обычный рендер.
 * Для больших списков реализует виртуализацию для оптимизации производительности.
 *
 * @param {object} props
 * @param {Array} props.items - Массив элементов для отображения
 * @param {Function} props.renderItem - Функция рендера элемента (item, index) => ReactNode
 * @param {number} props.itemHeight - Примерная высота элемента в пикселях
 * @param {object} props.columns - Количество колонок для разных брейкпоинтов
 * @param {number} props.gap - Отступ между элементами
 * @param {string} props.height - Высота контейнера (по умолчанию auto для маленьких списков)
 */
const VirtualizedGrid = memo(function VirtualizedGrid({
  items = [],
  renderItem,
  itemHeight = 300,
  columns = { base: 1, md: 2, lg: 3 },
  gap = 6,
  height,
  ...rest
}) {
  const containerRef = useRef(null);
  const [scrollTop, setScrollTop] = React.useState(0);
  const [containerHeight, setContainerHeight] = React.useState(0);

  // Responsive columns
  const columnCount = useBreakpointValue(columns) || 1;

  // Определяем, нужна ли виртуализация
  const shouldVirtualize = items.length > VIRTUALIZATION_THRESHOLD;

  // Вычисляем количество строк
  const rowCount = Math.ceil(items.length / columnCount);

  // Общая высота контента
  const totalHeight = rowCount * (itemHeight + (typeof gap === "number" ? gap * 4 : 24));

  // Обработчик скролла с throttle
  const handleScroll = useCallback(
    (e) => {
      if (!shouldVirtualize) return;

      // Используем requestAnimationFrame для throttle
      requestAnimationFrame(() => {
        setScrollTop(e.target.scrollTop);
      });
    },
    [shouldVirtualize],
  );

  // ResizeObserver для отслеживания размера контейнера
  React.useEffect(() => {
    if (!shouldVirtualize || !containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [shouldVirtualize]);

  // Вычисляем видимые элементы
  const visibleItems = useMemo(() => {
    if (!shouldVirtualize) {
      return items.map((item, index) => ({ item, index }));
    }

    const rowHeight = itemHeight + (typeof gap === "number" ? gap * 4 : 24);
    const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - OVERSCAN);
    const endRow = Math.min(
      rowCount,
      Math.ceil((scrollTop + containerHeight) / rowHeight) + OVERSCAN,
    );

    const startIndex = startRow * columnCount;
    const endIndex = Math.min(items.length, endRow * columnCount);

    return items.slice(startIndex, endIndex).map((item, i) => ({
      item,
      index: startIndex + i,
    }));
  }, [items, shouldVirtualize, scrollTop, containerHeight, itemHeight, gap, columnCount, rowCount]);

  // Для маленьких списков - простой рендер без виртуализации
  if (!shouldVirtualize) {
    return (
      <SimpleGrid columns={columns} spacing={gap} {...rest}>
        {items.map((item, index) => (
          <Box key={item.id || index}>{renderItem(item, index)}</Box>
        ))}
      </SimpleGrid>
    );
  }

  // Для больших списков - виртуализированный рендер
  const rowHeight = itemHeight + (typeof gap === "number" ? gap * 4 : 24);

  return (
    <Box
      ref={containerRef}
      height={height || "600px"}
      overflow="auto"
      onScroll={handleScroll}
      {...rest}
    >
      <Box position="relative" height={`${totalHeight}px`}>
        <SimpleGrid
          columns={columns}
          spacing={gap}
          position="absolute"
          top={0}
          left={0}
          right={0}
          style={{
            transform: `translateY(${Math.floor(visibleItems[0]?.index / columnCount || 0) * rowHeight}px)`,
          }}
        >
          {visibleItems.map(({ item, index }) => (
            <Box key={item.id || index}>{renderItem(item, index)}</Box>
          ))}
        </SimpleGrid>
      </Box>
    </Box>
  );
});

export default VirtualizedGrid;
