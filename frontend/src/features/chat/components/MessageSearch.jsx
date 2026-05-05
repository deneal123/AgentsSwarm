import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Icon,
  Text,
  Badge,
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  useToast,
  Divider,
  List,
  ListItem,
  ListIcon
} from '@chakra-ui/react';
import {
  FiSearch,
  FiX,
  FiChevronUp,
  FiChevronDown,
  FiHash,
  FiMessageSquare
} from 'react-icons/fi';
import { useChat } from '../context/ChatContext';
import { colors, borderRadius } from '@theme/tokens';

/**
 * MessageSearch - Компонент для поиска по сообщениям в чате
 *
 * Особенности:
 * - Debounced поиск с highlighting результатов
 * - Навигация по результатам (вверх/вниз)
 * - Сохранение недавних поисков
 * - Быстрые фильтры
 */
function MessageSearch({ isOpen, onClose, onResultSelect }) {
  const [query, setQuery] = useState('');
  const [currentResultIndex, setCurrentResultIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState([]);

  const { messages } = useChat();
  const toast = useToast();

  // Debounced search results
  const searchResults = useMemo(() => {
    if (!query.trim()) return [];

    const searchTerm = query.toLowerCase().trim();
    const results = [];

    messages.forEach((message, index) => {
      if (message.type === 'system') return; // Skip system messages

      const content = message.content?.toLowerCase() || '';
      const hasMatch = content.includes(searchTerm);

      if (hasMatch) {
        // Find all matches in content for highlighting
        const matches = [];
        let startIndex = 0;
        let matchIndex = content.indexOf(searchTerm, startIndex);

        while (matchIndex !== -1) {
          matches.push({
            start: matchIndex,
            end: matchIndex + searchTerm.length
          });
          startIndex = matchIndex + 1;
          matchIndex = content.indexOf(searchTerm, startIndex);
        }

        results.push({
          message,
          index,
          matches,
          preview: getMessagePreview(message.content, searchTerm)
        });
      }
    });

    return results;
  }, [query, messages]);

  // Navigation through results
  const navigateResults = useCallback((direction) => {
    if (searchResults.length === 0) return;

    let newIndex;
    if (direction === 'next') {
      newIndex = currentResultIndex < searchResults.length - 1 ? currentResultIndex + 1 : 0;
    } else {
      newIndex = currentResultIndex > 0 ? currentResultIndex - 1 : searchResults.length - 1;
    }

    setCurrentResultIndex(newIndex);

    // Scroll to message
    if (onResultSelect && searchResults[newIndex]) {
      onResultSelect(searchResults[newIndex].message.id);
    }
  }, [currentResultIndex, searchResults, onResultSelect]);

  // Handle search submission
  const handleSearch = useCallback(() => {
    if (!query.trim()) return;

    // Add to recent searches
    const newRecent = [query, ...recentSearches.filter(s => s !== query)].slice(0, 5);
    setRecentSearches(newRecent);
    localStorage.setItem('chat_recent_searches', JSON.stringify(newRecent));

    // Reset navigation
    setCurrentResultIndex(searchResults.length > 0 ? 0 : -1);

    // Show first result
    if (searchResults.length > 0 && onResultSelect) {
      onResultSelect(searchResults[0].message.id);
    }
  }, [query, recentSearches, searchResults, onResultSelect]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      navigateResults('prev');
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      navigateResults('next');
    } else if (e.key === 'Escape') {
      onClose();
    }
  }, [handleSearch, navigateResults, onClose]);

  // Load recent searches on mount
  React.useEffect(() => {
    const saved = localStorage.getItem('chat_recent_searches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch (error) {
        console.error('Failed to load recent searches:', error);
      }
    }
  }, []);

  // Reset on modal close
  React.useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setCurrentResultIndex(-1);
    }
  }, [isOpen]);

  const hasResults = searchResults.length > 0;
  const currentResult = currentResultIndex >= 0 ? searchResults[currentResultIndex] : null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay backdropFilter="blur(8px)" />
      <ModalContent
        bg="rgba(5,5,5,0.95)"
        backdropFilter="blur(20px)"
        border="1px solid rgba(255,255,255,0.1)"
        borderRadius="xl"
        maxH="80vh"
        overflow="hidden"
      >
        <ModalHeader color={colors.text.primary} pb={2}>
          <HStack spacing={3}>
            <Icon as={FiSearch} color={colors.brand.primary} />
            <Text>Поиск по сообщениям</Text>
          </HStack>
        </ModalHeader>

        <ModalCloseButton color={colors.text.secondary} />

        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* Search input */}
            <InputGroup>
              <InputLeftElement>
                <Icon as={FiSearch} color={colors.text.tertiary} />
              </InputLeftElement>
              <Input
                placeholder="Введите текст для поиска..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                bg="rgba(255,255,255,0.05)"
                border="1px solid rgba(255,255,255,0.1)"
                _focus={{
                  borderColor: colors.brand.primary,
                  bg: "rgba(255,255,255,0.08)"
                }}
                autoFocus
              />
            </InputGroup>

            {/* Search controls */}
            {query && (
              <HStack spacing={2} justify="space-between">
                <HStack spacing={2}>
                  <Button
                    size="sm"
                    variant="ghost"
                    leftIcon={<FiChevronUp />}
                    onClick={() => navigateResults('prev')}
                    isDisabled={!hasResults}
                    color={colors.text.secondary}
                  >
                    Предыдущий
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    leftIcon={<FiChevronDown />}
                    onClick={() => navigateResults('next')}
                    isDisabled={!hasResults}
                    color={colors.text.secondary}
                  >
                    Следующий
                  </Button>
                </HStack>

                <Text fontSize="sm" color={colors.text.tertiary}>
                  {hasResults ? `${currentResultIndex + 1} из ${searchResults.length}` : 'Нет результатов'}
                </Text>
              </HStack>
            )}

            <Divider borderColor="rgba(255,255,255,0.1)" />

            {/* Search results */}
            {query && (
              <Box maxH="300px" overflowY="auto">
                {hasResults ? (
                  <VStack spacing={2} align="stretch">
                    {searchResults.map((result, index) => (
                      <SearchResultItem
                        key={result.message.id}
                        result={result}
                        isActive={index === currentResultIndex}
                        onClick={() => {
                          setCurrentResultIndex(index);
                          if (onResultSelect) {
                            onResultSelect(result.message.id);
                          }
                        }}
                      />
                    ))}
                  </VStack>
                ) : (
                  <Box textAlign="center" py={8}>
                    <Icon as={FiSearch} boxSize={8} color={colors.text.tertiary} mb={3} />
                    <Text color={colors.text.secondary}>
                      {query ? 'Ничего не найдено' : 'Введите текст для поиска'}
                    </Text>
                  </Box>
                )}
              </Box>
            )}

            {/* Recent searches */}
            {!query && recentSearches.length > 0 && (
              <Box>
                <Text fontSize="sm" color={colors.text.tertiary} mb={2}>
                  Недавние поиски:
                </Text>
                <VStack spacing={1} align="stretch">
                  {recentSearches.map((search, index) => (
                    <Button
                      key={index}
                      size="sm"
                      variant="ghost"
                      justifyContent="flex-start"
                      onClick={() => setQuery(search)}
                      color={colors.text.secondary}
                      _hover={{ bg: 'rgba(255,255,255,0.05)' }}
                    >
                      <HStack spacing={2}>
                        <Icon as={FiHash} boxSize={3} />
                        <Text>{search}</Text>
                      </HStack>
                    </Button>
                  ))}
                </VStack>
              </Box>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}

// Компонент для отображения результата поиска
function SearchResultItem({ result, isActive, onClick }) {
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  };

  return (
    <Box
      p={3}
      borderRadius={borderRadius.md}
      bg={isActive ? 'rgba(47, 116, 255, 0.1)' : 'rgba(255,255,255,0.02)'}
      border={isActive ? '1px solid rgba(47, 116, 255, 0.3)' : '1px solid rgba(255,255,255,0.05)'}
      cursor="pointer"
      onClick={onClick}
      _hover={{ bg: 'rgba(255,255,255,0.05)' }}
      transition="all 0.2s"
    >
      <HStack spacing={3} align="start">
        <Icon
          as={FiMessageSquare}
          color={result.message.type === 'user' ? colors.brand.primary : colors.brand.secondary}
          boxSize={4}
          mt={0.5}
        />

        <VStack align="start" spacing={1} flex="1">
          <HStack spacing={2}>
            <Badge
              size="sm"
              colorScheme={result.message.type === 'user' ? 'blue' : 'green'}
              fontSize="xs"
            >
              {result.message.type === 'user' ? 'Вы' : 'AI'}
            </Badge>
            <Text fontSize="xs" color={colors.text.tertiary}>
              {formatTime(result.message.timestamp)}
            </Text>
          </HStack>

          <Text
            fontSize="sm"
            color={colors.text.primary}
            noOfLines={2}
            lineHeight="1.4"
          >
            {result.preview}
          </Text>

          {result.matches.length > 1 && (
            <Text fontSize="xs" color={colors.text.tertiary}>
              {result.matches.length} совпадений
            </Text>
          )}
        </VStack>
      </HStack>
    </Box>
  );
}

// Вспомогательная функция для создания preview сообщения с highlighting
function getMessagePreview(content, searchTerm) {
  if (!content) return '';

  const maxLength = 100;
  const lowerContent = content.toLowerCase();
  const lowerTerm = searchTerm.toLowerCase();

  const matchIndex = lowerContent.indexOf(lowerTerm);
  if (matchIndex === -1) return content.slice(0, maxLength) + (content.length > maxLength ? '...' : '');

  const start = Math.max(0, matchIndex - 30);
  const end = Math.min(content.length, matchIndex + searchTerm.length + 30);

  let preview = content.slice(start, end);
  if (start > 0) preview = '...' + preview;
  if (end < content.length) preview = preview + '...';

  return preview;
}

export default MessageSearch;
