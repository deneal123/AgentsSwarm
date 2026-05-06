import React, { Component } from "react";
import { Box, VStack, Text, Button, Icon, Code } from "@chakra-ui/react";
import { WarningTwoIcon } from "@chakra-ui/icons";
import { colors, borderRadius } from "@theme/tokens";

/**
 * Error Boundary для перехвата ошибок в дереве компонентов
 * Предоставляет graceful degradation при критических ошибках
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
    // Привязка методов к this
    this.handleReset = this.handleReset.bind(this);
    this.handleReload = this.handleReload.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });

    // Логирование ошибки
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    // Отправка на сервер аналитики в production
    if (process.env.NODE_ENV === "production" && this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset() {
    this.setState({ hasError: false, error: null, errorInfo: null });

    // Вызов callback при сбросе
    if (this.props.onReset) {
      this.props.onReset();
    }
  }

  handleReload() {
    window.location.reload();
  }

  render() {
    const { hasError, error, errorInfo } = this.state;
    const {
      children,
      fallback,
      fallbackRender,
      showDetails = process.env.NODE_ENV === "development",
      level = "page", // "page" | "section" | "component"
    } = this.props;

    if (hasError) {
      // Кастомный fallback через render prop
      if (fallbackRender) {
        return fallbackRender({
          error,
          errorInfo,
          reset: this.handleReset,
          reload: this.handleReload,
        });
      }

      // Кастомный fallback компонент
      if (fallback) {
        return fallback;
      }

      // Дефолтный UI в зависимости от уровня
      return (
        <ErrorFallback
          error={error}
          errorInfo={errorInfo}
          level={level}
          showDetails={showDetails}
          onReset={this.handleReset}
          onReload={this.handleReload}
        />
      );
    }

    return children;
  }
}

/**
 * Fallback UI компонент
 */
function ErrorFallback({ error, errorInfo, level, showDetails, onReset, onReload }) {
  const isPage = level === "page";
  const isSection = level === "section";

  const containerStyles = {
    page: {
      minH: "60vh",
      p: 8,
    },
    section: {
      p: 6,
      borderRadius: borderRadius.xl,
      border: "1px solid",
      borderColor: "rgba(239, 68, 68, 0.3)",
      bg: "rgba(239, 68, 68, 0.05)",
    },
    component: {
      p: 4,
      borderRadius: borderRadius.lg,
      border: "1px dashed",
      borderColor: "rgba(239, 68, 68, 0.4)",
    },
  };

  return (
    <Box {...containerStyles[level]}>
      <VStack spacing={4} align="center" justify="center" h="full">
        <Icon as={WarningTwoIcon} boxSize={isPage ? 16 : isSection ? 12 : 8} color="red.400" />

        <VStack spacing={2} textAlign="center">
          <Text
            fontSize={isPage ? "2xl" : isSection ? "xl" : "lg"}
            fontWeight="bold"
            color={colors.text.primary}
          >
            {isPage ? "Что-то пошло не так" : "Ошибка компонента"}
          </Text>

          <Text fontSize={isPage ? "md" : "sm"} color={colors.text.secondary} maxW="400px">
            {isPage
              ? "Произошла непредвиденная ошибка. Попробуйте обновить страницу."
              : "Этот компонент временно недоступен."}
          </Text>
        </VStack>

        {showDetails && error && (
          <Box
            maxW="600px"
            w="full"
            p={4}
            bg="rgba(0,0,0,0.3)"
            borderRadius={borderRadius.md}
            overflow="auto"
          >
            <Code colorScheme="red" display="block" whiteSpace="pre-wrap" fontSize="xs" p={2}>
              {error.toString()}
              {errorInfo?.componentStack && (
                <>
                  {"\n\nComponent Stack:"}
                  {errorInfo.componentStack}
                </>
              )}
            </Code>
          </Box>
        )}

        <VStack spacing={2}>
          <Button colorScheme="blue" size={isPage ? "lg" : "md"} onClick={onReset}>
            Попробовать снова
          </Button>

          {isPage && (
            <Button variant="ghost" size="md" onClick={onReload}>
              Перезагрузить страницу
            </Button>
          )}
        </VStack>
      </VStack>
    </Box>
  );
}

/**
 * HOC для оборачивания компонентов в Error Boundary
 */
export function withErrorBoundary(Component, errorBoundaryProps = {}) {
  const WrappedComponent = (props) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name || "Component"})`;

  return WrappedComponent;
}

/**
 * Хук для использования с функциональными компонентами
 * Позволяет программно триггерить ошибку для тестирования
 */
export function useErrorHandler() {
  const [error, setError] = React.useState(null);

  if (error) {
    throw error;
  }

  return {
    showBoundary: (error) => setError(error),
    reset: () => setError(null),
  };
}

export default ErrorBoundary;
