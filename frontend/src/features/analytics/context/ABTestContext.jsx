import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAnalytics } from './AnalyticsContext';

// A/B Testing Context
const ABTestContext = createContext(null);

// Hash функция для консистентного распределения пользователей
function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
}

// A/B Test Provider
export function ABTestProvider({ children, userId = null, tests = {} }) {
  const [activeTests, setActiveTests] = useState({});
  const [testResults, setTestResults] = useState({});
  const { trackEvent } = useAnalytics();

  // Идентификатор пользователя для консистентного распределения
  const userIdentifier = userId || localStorage.getItem('user_id') || 'anonymous';

  // Инициализация тестов
  useEffect(() => {
    const initializedTests = {};

    Object.entries(tests).forEach(([testName, testConfig]) => {
      const variant = getVariantForUser(testName, testConfig, userIdentifier);
      initializedTests[testName] = {
        ...testConfig,
        assignedVariant: variant,
        startedAt: new Date().toISOString(),
      };

      // Отслеживание exposure
      trackEvent('ab_test_exposure', {
        testName,
        variant,
        userId,
      });
    });

    setActiveTests(initializedTests);

    // Сохранение в localStorage для persistence
    localStorage.setItem('ab_tests', JSON.stringify(initializedTests));
  }, [tests, userIdentifier, trackEvent, userId]);

  // Загрузка сохраненных тестов
  useEffect(() => {
    const savedTests = localStorage.getItem('ab_tests');
    if (savedTests) {
      try {
        setActiveTests(JSON.parse(savedTests));
      } catch (error) {
        console.error('Failed to load saved A/B tests:', error);
      }
    }
  }, []);

  // Получение варианта для пользователя
  const getVariantForUser = useCallback((testName, testConfig, userId) => {
    const { variants = [], weights = [] } = testConfig;

    if (variants.length === 0) return null;

    // Создание консистентного распределения на основе userId и testName
    const hash = hashString(`${userId}_${testName}`);
    const normalizedHash = hash / 0x7FFFFFFF; // Normalize to 0-1

    // Распределение по весам
    let cumulativeWeight = 0;
    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);

    for (let i = 0; i < variants.length; i++) {
      cumulativeWeight += weights[i] || 1; // Default weight = 1
      if (normalizedHash <= cumulativeWeight / totalWeight) {
        return variants[i];
      }
    }

    // Fallback to first variant
    return variants[0];
  }, []);

  // Отслеживание конверсии
  const trackConversion = useCallback((testName, goal, metadata = {}) => {
    const test = activeTests[testName];
    if (!test) {
      console.warn(`A/B test "${testName}" not found`);
      return;
    }

    const conversion = {
      testName,
      variant: test.assignedVariant,
      goal,
      timestamp: new Date().toISOString(),
      metadata,
    };

    // Обновление результатов
    setTestResults(prev => ({
      ...prev,
      [testName]: {
        ...prev[testName],
        conversions: [...(prev[testName]?.conversions || []), conversion],
      },
    }));

    // Отправка аналитики
    trackEvent('ab_test_conversion', {
      testName,
      variant: test.assignedVariant,
      goal,
      metadata,
    });
  }, [activeTests, trackEvent]);

  // Получение активного варианта для теста
  const getVariant = useCallback((testName) => {
    return activeTests[testName]?.assignedVariant || null;
  }, [activeTests]);

  // Проверка, активен ли тест
  const isTestActive = useCallback((testName) => {
    return !!activeTests[testName];
  }, [activeTests]);

  // Получение результатов теста
  const getTestResults = useCallback((testName) => {
    const test = activeTests[testName];
    const results = testResults[testName];

    if (!test || !results) return null;

    // Простой статистический анализ
    const conversions = results.conversions || [];
    const variant = test.assignedVariant;

    return {
      testName,
      variant,
      conversionsCount: conversions.length,
      conversionRate: conversions.length > 0 ? 1 : 0, // Упрощенный расчет
      startDate: test.startedAt,
      goals: conversions.map(c => c.goal),
    };
  }, [activeTests, testResults]);

  // Завершение теста
  const endTest = useCallback((testName) => {
    setActiveTests(prev => {
      const updated = { ...prev };
      delete updated[testName];
      localStorage.setItem('ab_tests', JSON.stringify(updated));
      return updated;
    });

    // Отправка финальных результатов
    const results = getTestResults(testName);
    if (results) {
      trackEvent('ab_test_ended', results);
    }
  }, [getTestResults, trackEvent]);

  // Context value
  const contextValue = {
    // State
    activeTests,
    testResults,

    // Methods
    getVariant,
    isTestActive,
    trackConversion,
    getTestResults,
    endTest,

    // Utilities
    userIdentifier,
  };

  return (
    <ABTestContext.Provider value={contextValue}>
      {children}
    </ABTestContext.Provider>
  );
}

// Hook для использования A/B тестирования
export function useABTest() {
  const context = useContext(ABTestContext);
  if (!context) {
    throw new Error('useABTest must be used within an ABTestProvider');
  }
  return context;
}

// Компонент для декларативного A/B тестирования
export function ABTestComponent({
  testName,
  variants,
  defaultVariant = null,
  children,
  onExposure = null,
  onConversion = null
}) {
  const { getVariant, trackConversion, isTestActive } = useABTest();

  // Если тест не активен, показываем default
  if (!isTestActive(testName)) {
    return defaultVariant || children;
  }

  const assignedVariant = getVariant(testName);

  // Callback при показе варианта
  React.useEffect(() => {
    if (onExposure && assignedVariant) {
      onExposure(assignedVariant);
    }
  }, [assignedVariant, onExposure]);

  // Если children - функция, передаем вариант
  if (typeof children === 'function') {
    return children(assignedVariant, (goal, metadata) => {
      trackConversion(testName, goal, metadata);
      if (onConversion) {
        onConversion(goal, metadata);
      }
    });
  }

  // Поиск соответствующего варианта в массиве variants
  const variantComponent = variants.find(v => v.name === assignedVariant)?.component;

  if (!variantComponent) {
    console.warn(`Variant "${assignedVariant}" not found in test "${testName}"`);
    return defaultVariant || children;
  }

  return variantComponent;
}

// HOC для A/B тестирования компонентов
export function withABTest(testName, variants) {
  return function(Component) {
    return function ABTestWrapper(props) {
      return (
        <ABTestComponent testName={testName} variants={variants}>
          {(variant, trackConversion) => (
            <Component
              {...props}
              abTestVariant={variant}
              trackConversion={trackConversion}
            />
          )}
        </ABTestComponent>
      );
    };
  };
}

export default ABTestContext;
