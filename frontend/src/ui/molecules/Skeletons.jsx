import React, { memo } from "react";
import { Box, Skeleton as ChakraSkeleton, SimpleGrid, VStack, HStack } from "@chakra-ui/react";
import { borderRadius } from "@theme/tokens";

/**
 * DatasetCardSkeleton - Скелетон для карточки датасета
 */
export const DatasetCardSkeleton = memo(function DatasetCardSkeleton() {
  return (
    <Box
      borderRadius={borderRadius.xl}
      bg="rgba(8,10,18,0.9)"
      border="1px solid"
      borderColor="rgba(255,255,255,0.1)"
      overflow="hidden"
      p={{ base: 5, md: 6 }}
    >
      <VStack align="stretch" spacing={5}>
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="flex-start" spacing={2} flex={1}>
            <HStack spacing={2}>
              <ChakraSkeleton height="22px" width="60px" borderRadius="full" />
              <ChakraSkeleton height="22px" width="40px" borderRadius="full" />
            </HStack>
            <ChakraSkeleton height="24px" width="80%" />
            <ChakraSkeleton height="14px" width="120px" />
          </VStack>
        </HStack>

        {/* Stats */}
        <HStack spacing={3}>
          {[1, 2, 3].map((i) => (
            <Box
              key={i}
              flex={1}
              p={3}
              borderRadius={borderRadius.lg}
              bg="rgba(255,255,255,0.02)"
              border="1px solid rgba(255,255,255,0.05)"
            >
              <VStack spacing={1}>
                <ChakraSkeleton height="14px" width="14px" borderRadius="full" />
                <ChakraSkeleton height="18px" width="40px" />
                <ChakraSkeleton height="10px" width="50px" />
              </VStack>
            </Box>
          ))}
        </HStack>

        {/* Date */}
        <ChakraSkeleton height="14px" width="180px" />

        {/* Tags */}
        <HStack spacing={2}>
          <ChakraSkeleton height="20px" width="60px" borderRadius="full" />
          <ChakraSkeleton height="20px" width="50px" borderRadius="full" />
        </HStack>

        {/* Actions */}
        <HStack justify="space-between" pt={2}>
          <ChakraSkeleton height="32px" width="90px" borderRadius="md" />
          <ChakraSkeleton height="32px" width="100px" borderRadius="md" />
        </HStack>
      </VStack>
    </Box>
  );
});

/**
 * DatasetGridSkeleton - Скелетон для сетки датасетов
 */
export const DatasetGridSkeleton = memo(function DatasetGridSkeleton({
  count = 6,
  columns = { base: 1, md: 2, lg: 3 },
}) {
  return (
    <SimpleGrid columns={columns} spacing={6}>
      {Array.from({ length: count }).map((_, i) => (
        <DatasetCardSkeleton key={i} />
      ))}
    </SimpleGrid>
  );
});

/**
 * TableRowSkeleton - Скелетон для строки таблицы
 */
export const TableRowSkeleton = memo(function TableRowSkeleton({ columns = 5 }) {
  return (
    <HStack spacing={4} p={4} borderBottom="1px solid" borderColor="rgba(255,255,255,0.05)">
      {Array.from({ length: columns }).map((_, i) => (
        <ChakraSkeleton key={i} height="20px" flex={1} />
      ))}
    </HStack>
  );
});

/**
 * TableSkeleton - Скелетон для таблицы
 */
export const TableSkeleton = memo(function TableSkeleton({ rows = 5, columns = 5 }) {
  return (
    <Box
      borderRadius={borderRadius.lg}
      border="1px solid"
      borderColor="rgba(255,255,255,0.1)"
      overflow="hidden"
    >
      {/* Header */}
      <HStack
        spacing={4}
        p={4}
        bg="rgba(255,255,255,0.02)"
        borderBottom="1px solid"
        borderColor="rgba(255,255,255,0.1)"
      >
        {Array.from({ length: columns }).map((_, i) => (
          <ChakraSkeleton key={i} height="16px" flex={1} />
        ))}
      </HStack>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <TableRowSkeleton key={i} columns={columns} />
      ))}
    </Box>
  );
});

/**
 * ChartSkeleton - Скелетон для графика
 */
export const ChartSkeleton = memo(function ChartSkeleton({ height = "300px" }) {
  return (
    <Box
      height={height}
      borderRadius={borderRadius.lg}
      bg="rgba(255,255,255,0.02)"
      border="1px solid"
      borderColor="rgba(255,255,255,0.1)"
      p={4}
      display="flex"
      alignItems="flex-end"
      justifyContent="space-around"
    >
      {/* Bar chart skeleton */}
      {Array.from({ length: 8 }).map((_, i) => (
        <ChakraSkeleton
          key={i}
          width="8%"
          height={`${30 + Math.random() * 60}%`}
          borderRadius="sm"
        />
      ))}
    </Box>
  );
});

/**
 * StatCardSkeleton - Скелетон для статистической карточки
 */
export const StatCardSkeleton = memo(function StatCardSkeleton() {
  return (
    <Box
      p={4}
      borderRadius={borderRadius.lg}
      bg="rgba(255,255,255,0.02)"
      border="1px solid"
      borderColor="rgba(255,255,255,0.1)"
    >
      <HStack spacing={4}>
        <ChakraSkeleton height="40px" width="40px" borderRadius="lg" />
        <VStack align="flex-start" spacing={1} flex={1}>
          <ChakraSkeleton height="14px" width="60px" />
          <ChakraSkeleton height="24px" width="80px" />
        </VStack>
      </HStack>
    </Box>
  );
});

/**
 * PageSkeleton - Скелетон для целой страницы
 */
export const PageSkeleton = memo(function PageSkeleton({ type = "grid" }) {
  return (
    <VStack spacing={8} align="stretch" p={6}>
      {/* Header */}
      <VStack align="flex-start" spacing={2}>
        <ChakraSkeleton height="32px" width="200px" />
        <ChakraSkeleton height="16px" width="400px" />
      </VStack>

      {/* Stats */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </SimpleGrid>

      {/* Content */}
      {type === "grid" ? <DatasetGridSkeleton count={6} /> : <TableSkeleton rows={8} columns={5} />}
    </VStack>
  );
});

const Skeletons = {
  DatasetCardSkeleton,
  DatasetGridSkeleton,
  TableRowSkeleton,
  TableSkeleton,
  ChartSkeleton,
  StatCardSkeleton,
  PageSkeleton,
};

export default Skeletons;
