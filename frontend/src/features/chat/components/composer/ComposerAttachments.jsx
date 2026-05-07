import React from 'react';
import { HStack, Icon, IconButton, Text } from '@chakra-ui/react';
import { FiFileText } from 'react-icons/fi';

function ComposerAttachments({ attachments, onClear }) {
  if (!attachments) {
    return null;
  }

  return (
    <HStack mt={2} px={2} py={1} bg="rgba(239,68,68,0.15)" borderRadius="lg" spacing={2}>
      <Icon as={FiFileText} color="red.300" boxSize={4} />
      <Text fontSize="xs" color="red.200" noOfLines={1}>
        {attachments.filename} ({attachments.file_type})
      </Text>
      <IconButton
        aria-label="Удалить файл"
        icon={<Text fontSize="xs">✕</Text>}
        size="xs"
        variant="ghost"
        onClick={onClear}
      />
    </HStack>
  );
}

export default ComposerAttachments;
