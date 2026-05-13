import {
  Box,
  HStack,
  IconButton,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { FiFile, FiTrash2 } from 'react-icons/fi';
import { CHAT_SCROLLBAR_SX, CHAT_THEME } from '../../chat/constants/theme';

function formatBytes(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileList({ files = [], isLoading = false, onDelete, emptyLabel = 'Файлы не загружены' }) {
  if (isLoading) {
    return (
      <HStack justify="center" py={8} color={CHAT_THEME.textTertiary}>
        <Spinner size="sm" />
        <Text fontSize="13px">Загружаем файлы…</Text>
      </HStack>
    );
  }

  if (files.length === 0) {
    return (
      <Text fontSize="13px" color={CHAT_THEME.textTertiary} textAlign="center" py={8}>
        {emptyLabel}
      </Text>
    );
  }

  return (
    <VStack spacing={2} align="stretch" sx={CHAT_SCROLLBAR_SX}>
      {files.map((file) => (
        <Box
          key={file.file_id}
          p={3}
          borderRadius="10px"
          bg="rgba(255,255,255,0.03)"
          border={`1px solid ${CHAT_THEME.panelBorder}`}
          _hover={{ bg: 'rgba(255,255,255,0.05)' }}
          transition="all 0.15s"
        >
          <HStack justify="space-between" align="center">
            <HStack spacing={3} flex="1" minW="0">
              <Box color="rgba(239,68,68,0.7)" flexShrink={0}>
                <FiFile size={15} />
              </Box>
              <VStack align="flex-start" spacing={0} flex="1" minW="0">
                <Text fontSize="13px" fontWeight="500" color={CHAT_THEME.textPrimary} noOfLines={1}>
                  {file.filename || file.file_url?.split('/').pop() || 'Файл'}
                </Text>
                <Text fontSize="11px" color={CHAT_THEME.textTertiary}>
                  {formatBytes(file.file_size)}
                  {file.created_at && ` · ${new Date(file.created_at).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })}`}
                </Text>
              </VStack>
            </HStack>
            {onDelete && (
              <IconButton
                icon={<FiTrash2 size={13} />}
                size="xs"
                variant="ghost"
                color={CHAT_THEME.textTertiary}
                _hover={{ color: '#f87171', bg: CHAT_THEME.accentSoft }}
                borderRadius="8px"
                aria-label="Удалить файл"
                onClick={() => onDelete(file.file_id)}
              />
            )}
          </HStack>
        </Box>
      ))}
    </VStack>
  );
}
