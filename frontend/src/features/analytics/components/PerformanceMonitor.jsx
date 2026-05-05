import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Box, VStack, HStack, Text, Progress, Badge, useToast } from '@chakra-ui/react';
import { FiZap, FiTrendingUp, FiTrendingDown, FiAlertTriangle } from 'react-icons/fi';
import { useAnalytics } from '../context/AnalyticsContext';

/**
 * PerformanceMonitor - Компонент для мониторинга производительности приложения
 *
 * Отслеживает:
 * - Core Web Vitals (FCP, LCP, CLS, FID, TTFB)
 * - Component render times
 * - Memory usage
 * - Long tasks
 * - Network requests
 */
function PerformanceMonitor({ isVisible = false, autoTrack = true }) {
  const { trackEvent } = useAnalytics();
  const [metrics, setMetrics] = useState({});
  const [alerts, setAlerts] = useState([]);
  const toast = useToast();

  // Refs для измерений
  const renderStartTime = useRef(null);
  const observerRef = useRef(null);
  const longTaskObserverRef = useRef(null);

  // Пороги для метрик (по рекомендациям Google)
  const thresholds = {
    FCP: { good: 1800, poor: 3000 },      // First Contentful Paint
    LCP: { good: 2500, poor: 4000 },      // Largest Contentful Paint
    CLS: { good: 0.1, poor: 0.25 },       // Cumulative Layout Shift
    FID: { good: 100, poor: 300 },        // First Input Delay
    TTFB: { good: 800, poor: 1800 },      // Time to First Byte
  };

  // Инициализация Web Vitals
  const initWebVitals = useCallback(() => {
    // Dynamically import web-vitals to avoid bundle bloat
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS((metric) => handleWebVital('CLS', metric));
      getFID((metric) => handleWebVital('FID', metric));
      getFCP((metric) => handleWebVital('FCP', metric));
      getLCP((metric) => handleWebVital('LCP', metric));
      getTTFB((metric) => handleWebVital('TTFB', metric));
    }).catch(error => {
      console.warn('Web Vitals not available:', error);
    });
  }, []);

  // Обработка Web Vitals метрик
  const handleWebVital = useCallback((name, metric) => {
    const value = metric.value;
    const threshold = thresholds[name];

    let rating = 'good';
    if (value > threshold.poor) rating = 'poor';
    else if (value > threshold.good) rating = 'needs-improvement';

    const metricData = {
      name,
      value,
      rating,
      timestamp: metric.timestamp || Date.now(),
      navigationType: metric.navigationType,
      delta: metric.delta,
    };

    setMetrics(prev => ({ ...prev, [name]: metricData }));

    // Отправка аналитики
    if (autoTrack) {
      trackEvent('performance_web_vital', {
        metric: name,
        value,
        rating,
        navigationType: metric.navigationType,
      });
    }

    // Создание алерта для плохих метрик
    if (rating === 'poor') {
      const alert = {
        id: `alert_${Date.now()}`,
        type: 'performance',
        severity: 'high',
        title: `Плохая производительность: ${name}`,
        message: `${name} = ${value}ms (порог: ${threshold.good}ms)`,
        timestamp: Date.now(),
        metric: name,
        value,
        threshold: threshold.good,
      };

      setAlerts(prev => [alert, ...prev.slice(0, 9)]); // Хранить последние 10 алертов

      toast({
        title: alert.title,
        description: alert.message,
        status: 'warning',
        duration: 5000,
      });
    }
  }, [thresholds, autoTrack, trackEvent, toast]);

  // Мониторинг долгих задач
  const initLongTaskMonitoring = useCallback(() => {
    if ('PerformanceObserver' in window) {
      longTaskObserverRef.current = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) { // Задачи дольше 50ms считаются долгими
            const longTaskData = {
              name: entry.name,
              duration: entry.duration,
              startTime: entry.startTime,
              timestamp: Date.now(),
            };

            // Отправка аналитики
            if (autoTrack) {
              trackEvent('performance_long_task', {
                duration: entry.duration,
                startTime: entry.startTime,
              });
            }

            // Создание алерта
            if (entry.duration > 100) {
              const alert = {
                id: `alert_${Date.now()}`,
                type: 'performance',
                severity: 'medium',
                title: 'Долгая задача обнаружена',
                message: `Задача выполнялась ${entry.duration.toFixed(0)}ms`,
                timestamp: Date.now(),
                duration: entry.duration,
              };

              setAlerts(prev => [alert, ...prev.slice(0, 9)]);
            }
          }
        }
      });

      longTaskObserverRef.current.observe({ entryTypes: ['longtask'] });
    }
  }, [autoTrack, trackEvent]);

  // Мониторинг использования памяти
  const trackMemoryUsage = useCallback(() => {
    if ('memory' in performance) {
      const memory = performance.memory;
      const memoryData = {
        used: memory.usedJSHeapSize,
        total: memory.totalJSHeapSize,
        limit: memory.jsHeapSizeLimit,
        usagePercent: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
        timestamp: Date.now(),
      };

      setMetrics(prev => ({ ...prev, memory: memoryData }));

      // Отправка аналитики
      if (autoTrack) {
        trackEvent('performance_memory', {
          usedMB: Math.round(memory.usedJSHeapSize / 1024 / 1024),
          totalMB: Math.round(memory.totalJSHeapSize / 1024 / 1024),
          limitMB: Math.round(memory.jsHeapSizeLimit / 1024 / 1024),
          usagePercent: memoryData.usagePercent,
        });
      }

      // Алерт при высоком использовании памяти
      if (memoryData.usagePercent > 80) {
        const alert = {
          id: `alert_${Date.now()}`,
          type: 'performance',
          severity: 'high',
          title: 'Высокое использование памяти',
          message: `Использовано ${memoryData.usagePercent.toFixed(1)}% доступной памяти`,
          timestamp: Date.now(),
          usagePercent: memoryData.usagePercent,
        };

        setAlerts(prev => [alert, ...prev.slice(0, 9)]);
      }
    }
  }, [autoTrack, trackEvent]);

  // Мониторинг сетевых запросов
  const initNetworkMonitoring = useCallback(() => {
    // Переопределение XMLHttpRequest для отслеживания
    const originalXHR = window.XMLHttpRequest;
    window.XMLHttpRequest = function() {
      const xhr = new originalXHR();
      const startTime = Date.now();

      xhr.addEventListener('loadend', () => {
        const duration = Date.now() - startTime;
        const networkData = {
          url: xhr.responseURL || 'unknown',
          method: 'GET', // Для простоты, можно расширить
          status: xhr.status,
          duration,
          size: xhr.response?.length || 0,
          timestamp: Date.now(),
        };

        // Отправка аналитики для медленных запросов
        if (duration > 1000 && autoTrack) { // Запросы дольше 1 секунды
          trackEvent('performance_network_slow', {
            url: networkData.url,
            duration,
            status: networkData.status,
          });
        }
      });

      return xhr;
    };

    // Также отслеживаем Fetch API
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
      const startTime = Date.now();
      const result = await originalFetch.apply(this, args);
      const duration = Date.now() - startTime;

      if (duration > 1000 && autoTrack) {
        trackEvent('performance_fetch_slow', {
          url: args[0],
          duration,
          method: args[1]?.method || 'GET',
        });
      }

      return result;
    };
  }, [autoTrack, trackEvent]);

  // Инициализация всех мониторов
  useEffect(() => {
    initWebVitals();
    initLongTaskMonitoring();
    initNetworkMonitoring();

    // Периодический мониторинг памяти
    const memoryInterval = setInterval(trackMemoryUsage, 30000); // Каждые 30 секунд

    // Отслеживание времени рендера компонента
    renderStartTime.current = performance.now();

    return () => {
      clearInterval(memoryInterval);
      if (longTaskObserverRef.current) {
        longTaskObserverRef.current.disconnect();
      }
    };
  }, [initWebVitals, initLongTaskMonitoring, initNetworkMonitoring, trackMemoryUsage]);

  // Отслеживание времени рендера
  useEffect(() => {
    if (renderStartTime.current) {
      const renderTime = performance.now() - renderStartTime.current;

      if (renderTime > 16.67 && autoTrack) { // Дольше одного кадра (60fps)
        trackEvent('performance_component_render_slow', {
          component: 'PerformanceMonitor',
          renderTime,
        });
      }
    }
  });

  // Очистка алертов
  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  const getRatingColor = (rating) => {
    switch (rating) {
      case 'good': return 'green';
      case 'needs-improvement': return 'yellow';
      case 'poor': return 'red';
      default: return 'gray';
    }
  };

  const getRatingIcon = (rating) => {
    switch (rating) {
      case 'good': return FiTrendingUp;
      case 'poor': return FiTrendingDown;
      default: return FiZap;
    }
  };

  if (!isVisible) return null;

  return (
    <Box
      p={4}
      bg="rgba(5,5,5,0.9)"
      backdropFilter="blur(10px)"
      border="1px solid rgba(255,255,255,0.1)"
      borderRadius="xl"
      maxW="600px"
    >
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="bold" color="white">
            Мониторинг производительности
          </Text>
          <HStack>
            <Badge colorScheme="green" fontSize="xs">
              Активен
            </Badge>
            {alerts.length > 0 && (
              <Badge colorScheme="red" fontSize="xs" cursor="pointer" onClick={clearAlerts}>
                {alerts.length} алертов
              </Badge>
            )}
          </HStack>
        </HStack>

        {/* Web Vitals */}
        <VStack spacing={3} align="stretch">
          <Text fontSize="sm" color="gray.300" fontWeight="medium">
            Core Web Vitals
          </Text>

          {Object.entries(metrics).map(([key, metric]) => {
            if (key === 'memory') return null;

            const Icon = getRatingIcon(metric.rating);
            const unit = key === 'CLS' ? '' : 'ms';

            return (
              <HStack key={key} justify="space-between" align="center">
                <HStack spacing={2}>
                  <Icon color={getRatingColor(metric.rating)} size={16} />
                  <Text fontSize="sm" color="white">{key}</Text>
                </HStack>
                <HStack spacing={2}>
                  <Text fontSize="sm" color="gray.300">
                    {metric.value?.toFixed(key === 'CLS' ? 3 : 0)}{unit}
                  </Text>
                  <Badge
                    size="sm"
                    colorScheme={getRatingColor(metric.rating)}
                    fontSize="xs"
                  >
                    {metric.rating === 'good' ? 'Хорошо' :
                     metric.rating === 'needs-improvement' ? 'Средне' : 'Плохо'}
                  </Badge>
                </HStack>
              </HStack>
            );
          })}
        </VStack>

        {/* Memory Usage */}
        {metrics.memory && (
          <VStack spacing={2} align="stretch">
            <Text fontSize="sm" color="gray.300" fontWeight="medium">
              Использование памяти
            </Text>
            <Progress
              value={metrics.memory.usagePercent}
              size="sm"
              colorScheme={metrics.memory.usagePercent > 80 ? 'red' : 'blue'}
              borderRadius="full"
            />
            <Text fontSize="xs" color="gray.400">
              {Math.round(metrics.memory.used / 1024 / 1024)}MB из{' '}
              {Math.round(metrics.memory.limit / 1024 / 1024)}MB
            </Text>
          </VStack>
        )}

        {/* Recent Alerts */}
        {alerts.length > 0 && (
          <VStack spacing={2} align="stretch">
            <HStack justify="space-between">
              <Text fontSize="sm" color="gray.300" fontWeight="medium">
                Последние алерты
              </Text>
              <Text
                fontSize="xs"
                color="red.300"
                cursor="pointer"
                onClick={clearAlerts}
              >
                Очистить
              </Text>
            </HStack>

            {alerts.slice(0, 3).map((alert) => (
              <HStack key={alert.id} p={2} bg="rgba(255,0,0,0.1)" borderRadius="md">
                <FiAlertTriangle color="red" size={14} />
                <VStack spacing={0} align="start" flex="1">
                  <Text fontSize="xs" color="red.200" fontWeight="medium">
                    {alert.title}
                  </Text>
                  <Text fontSize="xs" color="red.300">
                    {alert.message}
                  </Text>
                </VStack>
              </HStack>
            ))}
          </VStack>
        )}
      </VStack>
    </Box>
  );
}

export default PerformanceMonitor;
