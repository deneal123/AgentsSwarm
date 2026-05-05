import React, { useState, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Grid,
  GridItem,
  Card,
  CardBody,
  Progress,
  Badge,
  Icon,
  Button,
  Select,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  SimpleGrid
} from '@chakra-ui/react';
import {
  FiTrendingUp,
  FiTrendingDown,
  FiUsers,
  FiMessageSquare,
  FiClock,
  FiAlertTriangle,
  FiBarChart3,
  FiEye,
  FiThumbsUp,
  FiStar,
  FiDownload
} from 'react-icons/fi';
import { useAnalytics } from '../context/AnalyticsContext';
import PerformanceDashboard from './PerformanceDashboard';

/**
 * AnalyticsDashboard - Панель аналитики с визуализацией метрик
 *
 * Показывает:
 * - Использование функций
 * - Производительность
 * - Обратную связь
 * - Ошибки и алерты
 */
function AnalyticsDashboard({ isOpen, onClose }) {
  const { stats, getStats } = useAnalytics();
  const [timeRange, setTimeRange] = useState('24h');
  const [selectedMetric, setSelectedMetric] = useState('overview');

  // Mock данные для демонстрации (в реальном приложении приходят с API)
  const mockData = useMemo(() => ({
    overview: {
      totalUsers: 1250,
      activeUsers: 340,
      totalMessages: 5670,
      avgSessionTime: '12m 34s',
      topFeatures: [
        { name: 'Поиск сообщений', usage: 85, trend: 'up' },
        { name: 'Голосовые сообщения', usage: 67, trend: 'up' },
        { name: 'Реакции', usage: 92, trend: 'up' },
        { name: 'Темы оформления', usage: 45, trend: 'down' },
      ]
    },
    performance: {
      avgLoadTime: 2.3,
      errorRate: 0.8,
      uptime: 99.7,
      coreWebVitals: {
        FCP: { value: 1.2, rating: 'good' },
        LCP: { value: 3.1, rating: 'needs-improvement' },
        CLS: { value: 0.08, rating: 'good' },
        FID: { value: 45, rating: 'good' },
      }
    },
    feedback: {
      totalFeedback: 156,
      avgRating: 4.2,
      categories: [
        { name: 'Общее впечатление', count: 89, avgRating: 4.5 },
        { name: 'Предложения функций', count: 34, avgRating: 3.8 },
        { name: 'Ошибки', count: 23, avgRating: 2.1 },
        { name: 'Производительность', count: 10, avgRating: 3.9 },
      ],
      recentFeedback: [
        { id: 1, rating: 5, message: 'Отличный интерфейс!', category: 'general', time: '2h ago' },
        { id: 2, rating: 3, message: 'Медленная загрузка', category: 'performance', time: '4h ago' },
        { id: 3, rating: 4, message: 'Хотелось бы темную тему', category: 'feature', time: '6h ago' },
      ]
    },
    errors: {
      totalErrors: 23,
      criticalErrors: 3,
      recentErrors: [
        { id: 1, type: 'JavaScript Error', message: 'TypeError: Cannot read property', count: 5, lastSeen: '1h ago' },
        { id: 2, type: 'API Error', message: 'Failed to fetch messages', count: 3, lastSeen: '2h ago' },
        { id: 3, type: 'Network Error', message: 'Connection timeout', count: 2, lastSeen: '3h ago' },
      ]
    }
  }), []);

  const getRatingColor = (rating) => {
    switch (rating) {
      case 'good': return 'green';
      case 'needs-improvement': return 'yellow';
      case 'poor': return 'red';
      default: return 'gray';
    }
  };

  const MetricCard = ({ title, value, icon, trend, subtitle, color = 'blue' }) => (
    <Card bg="rgba(255,255,255,0.05)" border="1px solid rgba(255,255,255,0.1)">
      <CardBody>
        <VStack spacing={2} align="start">
          <HStack justify="space-between" w="full">
            <Icon as={icon} color={`${color}.400`} boxSize={5} />
            {trend && (
              <Icon
                as={trend === 'up' ? FiTrendingUp : FiTrendingDown}
                color={trend === 'up' ? 'green.400' : 'red.400'}
                boxSize={4}
              />
            )}
          </HStack>
          <Text fontSize="2xl" fontWeight="bold" color="white">
            {value}
          </Text>
          <Text fontSize="sm" color="gray.300" fontWeight="medium">
            {title}
          </Text>
          {subtitle && (
            <Text fontSize="xs" color="gray.400">
              {subtitle}
            </Text>
          )}
        </VStack>
      </CardBody>
    </Card>
  );

  const WebVitalsCard = ({ metric, value, rating }) => (
    <Box p={4} bg="rgba(255,255,255,0.05)" borderRadius="lg" border="1px solid rgba(255,255,255,0.1)">
      <VStack spacing={2} align="center">
        <Text fontSize="sm" color="gray.300" fontWeight="medium">
          {metric}
        </Text>
        <Text fontSize="xl" color="white" fontWeight="bold">
          {metric === 'CLS' ? value : `${value}${metric === 'FID' ? 'ms' : 's'}`}
        </Text>
        <Badge colorScheme={getRatingColor(rating)} size="sm">
          {rating === 'good' ? 'Хорошо' : rating === 'needs-improvement' ? 'Средне' : 'Плохо'}
        </Badge>
      </VStack>
    </Box>
  );

  const exportData = () => {
    const data = {
      timestamp: new Date().toISOString(),
      timeRange,
      metrics: mockData,
      analyticsStats: stats,
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics-export-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl">
      <ModalOverlay backdropFilter="blur(8px)" />
      <ModalContent
        bg="rgba(5,5,5,0.95)"
        backdropFilter="blur(20px)"
        border="1px solid rgba(255,255,255,0.1)"
        borderRadius="xl"
        maxH="90vh"
        overflow="hidden"
      >
        <ModalHeader color="white">
          <HStack justify="space-between" w="full">
            <HStack spacing={3}>
              <Icon as={FiBarChart3} color="brand.primary" />
              <Text>Аналитика и метрики</Text>
            </HStack>

            <HStack spacing={3}>
              <Select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                size="sm"
                bg="rgba(255,255,255,0.05)"
                border="1px solid rgba(255,255,255,0.1)"
                color="white"
                w="120px"
              >
                <option value="1h">1 час</option>
                <option value="24h">24 часа</option>
                <option value="7d">7 дней</option>
                <option value="30d">30 дней</option>
              </Select>

              <Button
                size="sm"
                variant="outline"
                leftIcon={<FiDownload />}
                onClick={exportData}
              >
                Экспорт
              </Button>
            </HStack>
          </HStack>
        </ModalHeader>

        <ModalCloseButton color="gray.400" />

        <ModalBody overflowY="auto" maxH="calc(90vh - 80px)">
          <Tabs variant="soft-rounded" colorScheme="brand">
            <TabList mb={4} bg="rgba(255,255,255,0.05)" p={1} borderRadius="lg">
              <Tab color="white" _selected={{ bg: 'brand.primary', color: 'white' }}>
                Обзор
              </Tab>
              <Tab color="white" _selected={{ bg: 'brand.primary', color: 'white' }}>
                Производительность
              </Tab>
              <Tab color="white" _selected={{ bg: 'brand.primary', color: 'white' }}>
                Обратная связь
              </Tab>
              <Tab color="white" _selected={{ bg: 'brand.primary', color: 'white' }}>
                Ошибки
              </Tab>
            </TabList>

            <TabPanels>
              {/* Обзор */}
              <TabPanel>
                <VStack spacing={6} align="stretch">
                  <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                    <MetricCard
                      title="Активные пользователи"
                      value={mockData.overview.activeUsers}
                      icon={FiUsers}
                      trend="up"
                      subtitle={`из ${mockData.overview.totalUsers} всего`}
                      color="green"
                    />
                    <MetricCard
                      title="Сообщений отправлено"
                      value={mockData.overview.totalMessages.toLocaleString()}
                      icon={FiMessageSquare}
                      trend="up"
                      subtitle="за выбранный период"
                      color="blue"
                    />
                    <MetricCard
                      title="Среднее время сессии"
                      value={mockData.overview.avgSessionTime}
                      icon={FiClock}
                      trend="up"
                      subtitle="время взаимодействия"
                      color="purple"
                    />
                    <MetricCard
                      title="Уровень удовлетворенности"
                      value="4.2"
                      icon={FiStar}
                      trend="up"
                      subtitle="из 5 звезд"
                      color="yellow"
                    />
                  </SimpleGrid>

                  <Box>
                    <Text fontSize="lg" fontWeight="bold" color="white" mb={4}>
                      Популярные функции
                    </Text>
                    <VStack spacing={3} align="stretch">
                      {mockData.overview.topFeatures.map((feature, index) => (
                        <Box
                          key={index}
                          p={4}
                          bg="rgba(255,255,255,0.05)"
                          borderRadius="lg"
                          border="1px solid rgba(255,255,255,0.1)"
                        >
                          <HStack justify="space-between" align="center">
                            <HStack spacing={3}>
                              <Text color="white" fontWeight="medium">
                                {feature.name}
                              </Text>
                              <Badge colorScheme={feature.trend === 'up' ? 'green' : 'red'} size="sm">
                                {feature.usage}%
                              </Badge>
                            </HStack>
                            <Progress
                              value={feature.usage}
                              size="sm"
                              colorScheme={feature.trend === 'up' ? 'green' : 'red'}
                              w="100px"
                              borderRadius="full"
                            />
                          </HStack>
                        </Box>
                      ))}
                    </VStack>
                  </Box>
                </VStack>
              </TabPanel>

              <TabPanel>
                <PerformanceDashboard />
              </TabPanel>

              {/* Обратная связь */}
              <TabPanel>
                <VStack spacing={6} align="stretch">
                  <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                    <MetricCard
                      title="Всего отзывов"
                      value={mockData.feedback.totalFeedback}
                      icon={FiMessageSquare}
                      trend="up"
                      subtitle="получено"
                      color="blue"
                    />
                    <MetricCard
                      title="Средний рейтинг"
                      value={mockData.feedback.avgRating}
                      icon={FiStar}
                      trend="up"
                      subtitle="из 5 звезд"
                      color="yellow"
                    />
                    <MetricCard
                      title="Положительные отзывы"
                      value="78%"
                      icon={FiThumbsUp}
                      trend="up"
                      subtitle="рейтинг 4+"
                      color="green"
                    />
                    <MetricCard
                      title="Ответы на отзывы"
                      value="92%"
                      icon={FiMessageSquare}
                      trend="up"
                      subtitle="вовлеченность"
                      color="purple"
                    />
                  </SimpleGrid>

                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                    <Box>
                      <Text fontSize="lg" fontWeight="bold" color="white" mb={4}>
                        Категории отзывов
                      </Text>
                      <VStack spacing={3} align="stretch">
                        {mockData.feedback.categories.map((category, index) => (
                          <Box
                            key={index}
                            p={3}
                            bg="rgba(255,255,255,0.05)"
                            borderRadius="lg"
                            border="1px solid rgba(255,255,255,0.1)"
                          >
                            <HStack justify="space-between" align="center">
                              <Text color="white" fontSize="sm">
                                {category.name}
                              </Text>
                              <HStack spacing={2}>
                                <Badge colorScheme="blue" size="sm">
                                  {category.count}
                                </Badge>
                                <Text color="yellow.400" fontSize="sm">
                                  {category.avgRating}★
                                </Text>
                              </HStack>
                            </HStack>
                          </Box>
                        ))}
                      </VStack>
                    </Box>

                    <Box>
                      <Text fontSize="lg" fontWeight="bold" color="white" mb={4}>
                        Последние отзывы
                      </Text>
                      <VStack spacing={3} align="stretch">
                        {mockData.feedback.recentFeedback.map((feedback) => (
                          <Box
                            key={feedback.id}
                            p={3}
                            bg="rgba(255,255,255,0.05)"
                            borderRadius="lg"
                            border="1px solid rgba(255,255,255,0.1)"
                          >
                            <HStack justify="space-between" align="center" mb={2}>
                              <HStack spacing={1}>
                                {[...Array(5)].map((_, i) => (
                                  <Icon
                                    key={i}
                                    as={FiStar}
                                    size={12}
                                    color={i < feedback.rating ? "yellow.400" : "gray.500"}
                                  />
                                ))}
                              </HStack>
                              <Text color="gray.400" fontSize="xs">
                                {feedback.time}
                              </Text>
                            </HStack>
                            <Text color="white" fontSize="sm">
                              {feedback.message}
                            </Text>
                          </Box>
                        ))}
                      </VStack>
                    </Box>
                  </SimpleGrid>
                </VStack>
              </TabPanel>

              {/* Ошибки */}
              <TabPanel>
                <VStack spacing={6} align="stretch">
                  <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                    <MetricCard
                      title="Всего ошибок"
                      value={mockData.errors.totalErrors}
                      icon={FiAlertTriangle}
                      trend="down"
                      subtitle="за период"
                      color="red"
                    />
                    <MetricCard
                      title="Критических ошибок"
                      value={mockData.errors.criticalErrors}
                      icon={FiAlertTriangle}
                      trend="down"
                      subtitle="нуждаются во внимании"
                      color="orange"
                    />
                    <MetricCard
                      title="Исправлено ошибок"
                      value="89%"
                      icon={FiTrendingUp}
                      trend="up"
                      subtitle="за последний месяц"
                      color="green"
                    />
                    <MetricCard
                      title="Время отклика"
                      value="< 2s"
                      icon={FiClock}
                      trend="down"
                      subtitle="среднее время"
                      color="blue"
                    />
                  </SimpleGrid>

                  <Box>
                    <Text fontSize="lg" fontWeight="bold" color="white" mb={4}>
                      Последние ошибки
                    </Text>
                    <VStack spacing={3} align="stretch">
                      {mockData.errors.recentErrors.map((error) => (
                        <Box
                          key={error.id}
                          p={4}
                          bg="rgba(255,255,255,0.05)"
                          borderRadius="lg"
                          border="1px solid rgba(255,255,255,0.1)"
                        >
                          <HStack justify="space-between" align="center" mb={2}>
                            <Badge colorScheme="red" size="sm">
                              {error.type}
                            </Badge>
                            <HStack spacing={2}>
                              <Text color="gray.400" fontSize="xs">
                                {error.lastSeen}
                              </Text>
                              <Badge colorScheme="orange" size="sm">
                                {error.count}x
                              </Badge>
                            </HStack>
                          </HStack>
                          <Text color="white" fontSize="sm">
                            {error.message}
                          </Text>
                        </Box>
                      ))}
                    </VStack>
                  </Box>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}

export default AnalyticsDashboard;
