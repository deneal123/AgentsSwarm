import React from 'react';
import { HStack, IconButton } from '@chakra-ui/react';
import { FiSend } from 'react-icons/fi';
import { CHAT_THEME } from '../../constants/theme';

function ComposerActions({ value, onSubmit, disabled }) {
  return (
    <HStack position="absolute" right={3} bottom="10px" spacing={1.5} zIndex={2}>
      <IconButton
        aria-label="Отправить"
        icon={<FiSend />}
        size="sm"
        bg={value.trim() && !disabled ? CHAT_THEME.accent : 'rgba(255,255,255,0.08)'}
        color="white"
        borderRadius="10px"
        _hover={{ bg: value.trim() && !disabled ? CHAT_THEME.accentHover : 'rgba(255,255,255,0.12)' }}
        _disabled={{ opacity: 0.4, cursor: 'not-allowed' }}
        isDisabled={!value.trim() || disabled}
        onClick={onSubmit}
      />
    </HStack>
  );
}

export default ComposerActions;
