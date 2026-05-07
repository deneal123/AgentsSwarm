import React from 'react';
import { IconButton } from '@chakra-ui/react';
import { FiMic } from 'react-icons/fi';
import { CHAT_THEME } from '../../constants/theme';

function ComposerVoiceControl({ recordingState, onToggle }) {
  return (
    <IconButton
      aria-label="Голосовой ввод"
      icon={<FiMic />}
      size="sm"
      variant="ghost"
      position="absolute"
      right={14}
      bottom="10px"
      zIndex={2}
      color={recordingState ? '#f87171' : CHAT_THEME.textTertiary}
      _hover={{ color: CHAT_THEME.textPrimary, bg: CHAT_THEME.panelHover }}
      borderRadius="9px"
      onClick={onToggle}
    />
  );
}

export default ComposerVoiceControl;
