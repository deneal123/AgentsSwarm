import { useRef } from 'react';
import { Box, Button, Progress, Text, VStack } from '@chakra-ui/react';
import { FiUpload } from 'react-icons/fi';
import { CHAT_THEME } from '@features/chat/constants/theme';

export function FileUploadButton({
  onUpload,
  isUploading = false,
  uploadProgress = 0,
  accept,
  label = 'Загрузить файл',
  disabled = false,
}) {
  const inputRef = useRef(null);

  const handleChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    await onUpload?.(file);
  };

  return (
    <VStack spacing={2} align="stretch">
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={handleChange}
      />
      <Button
        leftIcon={<FiUpload size={13} />}
        size="sm"
        h="36px"
        borderRadius="10px"
        fontSize="13px"
        fontWeight="600"
        bg={CHAT_THEME.accentSoft}
        color="#fca5a5"
        border="1px solid rgba(239,68,68,0.3)"
        _hover={{ bg: 'rgba(239,68,68,0.22)', borderColor: 'rgba(239,68,68,0.45)' }}
        isLoading={isUploading}
        isDisabled={disabled || isUploading}
        onClick={() => inputRef.current?.click()}
      >
        {label}
      </Button>
      {isUploading && (
        <Box>
          <Progress
            value={uploadProgress}
            size="xs"
            borderRadius="full"
            bg="rgba(255,255,255,0.06)"
            sx={{ '& > div': { background: 'linear-gradient(90deg, rgba(248,113,113,0.85), rgba(239,68,68,0.98))' } }}
          />
          <Text fontSize="10px" color={CHAT_THEME.textTertiary} mt={1}>
            {uploadProgress}%
          </Text>
        </Box>
      )}
    </VStack>
  );
}
