import React, { useEffect, useMemo, useState } from 'react';
import { Box, SimpleGrid, Text, VStack, Badge, Progress, Spinner, Center } from '@chakra-ui/react';

const formatValue = (metricName, value) => {
  if (metricName === 'CLS') return value.toFixed(3);
  if (metricName === 'FID' || metricName === 'INP') return `${value.toFixed(0)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
};

const ratingColor = (rate) => {
  if (rate >= 0.75) return 'green';
  if (rate >= 0.5) return 'yellow';
  return 'red';
};

function PerformanceDashboard() {
  const [summary, setSummary] = useState({ metrics: [], total_events: 0, updated_at: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const response = await fetch('/api/analytics/vitals/summary');
        if (!response.ok) {
          throw new Error('failed');
        }
        const data = await response.json();
        if (mounted) {
          setSummary(data);
        }
      } catch (error) {
        if (mounted) {
          setSummary({ metrics: [], total_events: 0, updated_at: null });
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    load();
    const interval = setInterval(load, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const sortedMetrics = useMemo(() => {
    return [...summary.metrics].sort((left, right) => right.count - left.count);
  }, [summary.metrics]);

  if (loading) {
    return (
      <Center minH="220px">
        <Spinner />
      </Center>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      <Box p={4} bg="rgba(255,255,255,0.05)" border="1px solid rgba(255,255,255,0.1)" borderRadius="lg">
        <Text color="white" fontWeight="bold">Собрано событий: {summary.total_events}</Text>
        <Text color="gray.400" fontSize="sm">Последнее обновление: {summary.updated_at ? new Date(summary.updated_at).toLocaleString() : 'нет данных'}</Text>
      </Box>

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
        {sortedMetrics.map((metric) => (
          <Box key={metric.name} p={4} bg="rgba(255,255,255,0.05)" border="1px solid rgba(255,255,255,0.1)" borderRadius="lg">
            <VStack align="stretch" spacing={3}>
              <Text color="white" fontWeight="bold">{metric.name}</Text>
              <Text color="gray.300" fontSize="sm">AVG: {formatValue(metric.name, metric.avg)} | P95: {formatValue(metric.name, metric.p95)}</Text>
              <Badge colorScheme={ratingColor(metric.good_rate)} w="fit-content">Good rate: {(metric.good_rate * 100).toFixed(1)}%</Badge>
              <Progress value={metric.good_rate * 100} size="sm" colorScheme={ratingColor(metric.good_rate)} borderRadius="full" />
              <Text color="gray.400" fontSize="xs">count: {metric.count} | needs-improvement: {(metric.needs_improvement_rate * 100).toFixed(1)}% | poor: {(metric.poor_rate * 100).toFixed(1)}%</Text>
            </VStack>
          </Box>
        ))}
      </SimpleGrid>
    </VStack>
  );
}

export default PerformanceDashboard;
