import React from 'react';
import { Textarea } from '@chakra-ui/react';
import { CHAT_FONT_FAMILY, CHAT_THEME } from '../../constants/theme';
import { COMPOSER_MAX_HEIGHT_PX, COMPOSER_MIN_HEIGHT_PX } from '../../constants/limits';

function ComposerInput({ value, onChange, onSubmit, disabled, onKeyDown, inputRef, composerHeightPx }) {
  return (
    <Textarea
      ref={inputRef}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        onKeyDown?.(e);
        if (e.defaultPrevented) {
          return;
        }
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          onSubmit();
        }
      }}
      placeholder="Напишите сообщение..."
      isDisabled={disabled}
      minH={`${COMPOSER_MIN_HEIGHT_PX}px`}
      maxH={`${COMPOSER_MAX_HEIGHT_PX}px`}
      h={`${composerHeightPx}px`}
      overflowY={composerHeightPx >= COMPOSER_MAX_HEIGHT_PX ? 'auto' : 'hidden'}
      resize="none"
      pl={12}
      pr={24}
      py="15px"
      borderRadius="16px"
      bg={CHAT_THEME.inputBg}
      border={`1.5px solid ${CHAT_THEME.inputBorder}`}
      color={CHAT_THEME.textPrimary}
      fontSize="15px"
      fontWeight="450"
      fontFamily={CHAT_FONT_FAMILY}
      lineHeight="1.6"
      _placeholder={{ color: CHAT_THEME.textTertiary }}
    />
  );
}

export default ComposerInput;
