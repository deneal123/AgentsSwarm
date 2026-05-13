import React, { forwardRef, useCallback, useImperativeHandle, useRef, useState } from 'react';
import { Box, Button, HStack, Icon, IconButton, Text } from '@chakra-ui/react';
import { FiPaperclip, FiSearch, FiSend } from 'react-icons/fi';
import { CHAT_FONT_FAMILY, CHAT_THEME } from '../../constants/theme';
import { COMPOSER_MAX_HEIGHT_PX, COMPOSER_MIN_HEIGHT_PX } from '../../constants/limits';
import ComposerShell from './ComposerShell';
import ComposerVoiceControl from './ComposerVoiceControl';
import ComposerAttachments from './ComposerAttachments';

// Isolated, uncontrolled composer — typing never re-renders ChatPageContainer
const ChatComposerPanel = forwardRef(function ChatComposerPanel(
  {
    onSubmit,
    disabled,
    webSearchEnabled,
    deepResearchEnabled,
    onToggleWebSearch,
    onToggleDeepResearch,
    modelLabel,
    isAuthenticated,
    remainingRequests,
    attachedFile,
    onClearAttachment,
    onFileUpload,
    onVoiceToggle,
    isRecording,
    fileInputRef,
  },
  ref,
) {
  const inputRef = useRef(null);
  const [height, setHeight] = useState(COMPOSER_MIN_HEIGHT_PX);
  const [hasText, setHasText] = useState(false);
  const frameRef = useRef(0);
  const onSubmitRef = useRef(onSubmit);
  onSubmitRef.current = onSubmit;

  useImperativeHandle(ref, () => ({
    clearInput() {
      if (inputRef.current) {
        inputRef.current.value = '';
        setHasText(false);
        recalcHeight();
      }
    },
    setInputValue(val) {
      if (inputRef.current) {
        inputRef.current.value = val;
        setHasText(!!val.trim());
        recalcHeight();
        inputRef.current.focus();
      }
    },
    focus() {
      inputRef.current?.focus();
    },
  }));

  const recalcHeight = useCallback(() => {
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => {
      const el = inputRef.current;
      if (!el) return;
      el.style.height = 'auto';
      const next = Math.min(COMPOSER_MAX_HEIGHT_PX, Math.max(COMPOSER_MIN_HEIGHT_PX, el.scrollHeight));
      setHeight((prev) => (prev === next ? prev : next));
      el.style.height = `${next}px`;
    });
  }, []);

  const handleInput = useCallback((e) => {
    setHasText(!!e.target.value.trim());
    recalcHeight();
  }, [recalcHeight]);

  const handleSubmit = useCallback(() => {
    if (disabled) return;
    const val = inputRef.current?.value.trim() ?? '';
    if (!val) return;
    onSubmitRef.current(val);
  }, [disabled]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const canSend = hasText && !disabled;

  return (
    <Box flexShrink={0} px={{ base: 3, md: 6, lg: 8 }} pt={3} pb={4}
      borderTop={`1px solid ${CHAT_THEME.panelBorder}`}
      bg={CHAT_THEME.inputStickyBg} backdropFilter="blur(20px)">
      <Box maxW="960px" mx="auto">
        <ComposerShell>
          <input type="file" ref={fileInputRef} style={{ display: 'none' }}
            accept=".txt,.md,.pdf,.docx,.csv,.json,.png,.jpg,.jpeg,.gif,.webp,.mp3,.wav,.ogg,.m4a,.webm"
            onChange={onFileUpload} />

          <IconButton aria-label="Прикрепить файл" icon={<FiPaperclip />} size="sm" variant="ghost"
            position="absolute" left={3} top="12px" zIndex={2}
            color={attachedFile ? '#f87171' : CHAT_THEME.textTertiary}
            _hover={{ color: CHAT_THEME.textPrimary, bg: CHAT_THEME.panelHover }}
            borderRadius="9px" onClick={() => fileInputRef.current?.click()} />

          <Box
            as="textarea"
            ref={inputRef}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Напишите сообщение..."
            disabled={disabled}
            style={{ height: `${height}px` }}
            sx={{
              minH: `${COMPOSER_MIN_HEIGHT_PX}px`,
              maxH: `${COMPOSER_MAX_HEIGHT_PX}px`,
              overflowY: height >= COMPOSER_MAX_HEIGHT_PX ? 'auto' : 'hidden',
              resize: 'none',
              width: '100%',
              pl: '48px',
              pr: '96px',
              py: '15px',
              borderRadius: '16px',
              bg: CHAT_THEME.inputBg,
              border: `1.5px solid ${CHAT_THEME.inputBorder}`,
              color: CHAT_THEME.textPrimary,
              fontSize: '15px',
              fontWeight: '450',
              fontFamily: CHAT_FONT_FAMILY,
              lineHeight: '1.6',
              outline: 'none',
              paddingLeft: '48px',
              paddingRight: '96px',
              paddingTop: '15px',
              paddingBottom: '15px',
              backgroundColor: CHAT_THEME.inputBg,
              borderWidth: '1.5px',
              borderStyle: 'solid',
              borderColor: CHAT_THEME.inputBorder,
              boxSizing: 'border-box',
              '&::placeholder': { color: CHAT_THEME.textTertiary },
              '&:focus': { outline: 'none', borderColor: 'rgba(239,68,68,0.4)', boxShadow: '0 0 0 3px rgba(239,68,68,0.08)' },
              '&:disabled': { opacity: 0.6, cursor: 'not-allowed' },
            }}
          />

          <ComposerVoiceControl recordingState={isRecording ? 'recording' : 'idle'} onToggle={onVoiceToggle} />

          <HStack position="absolute" right={3} bottom="10px" spacing={1.5} zIndex={2}>
            <IconButton aria-label="Отправить" icon={<FiSend />} size="sm"
              bg={canSend ? CHAT_THEME.accent : 'rgba(255,255,255,0.08)'} color="white"
              borderRadius="10px"
              _hover={{ bg: canSend ? CHAT_THEME.accentHover : 'rgba(255,255,255,0.12)' }}
              _disabled={{ opacity: 0.4, cursor: 'not-allowed' }}
              isDisabled={!canSend} onClick={handleSubmit} />
          </HStack>
        </ComposerShell>

        <ComposerAttachments attachments={attachedFile} onClear={onClearAttachment} />

        <HStack mt={2.5} spacing={2} justify="space-between" flexWrap="wrap">
          <HStack spacing={1.5}>
            {[
              { label: 'Веб-поиск', icon: '🌐', active: webSearchEnabled, toggle: onToggleWebSearch },
              { label: 'Deep Research', icon: '🔬', active: deepResearchEnabled, toggle: onToggleDeepResearch },
            ].map(({ label, icon, active, toggle }) => (
              <Button key={label} size="xs" borderRadius="8px" variant="unstyled" display="flex"
                alignItems="center" gap={1} px={3} h="26px" fontSize="12px" fontWeight="600"
                fontFamily={CHAT_FONT_FAMILY}
                bg={active ? CHAT_THEME.accentSoft : CHAT_THEME.panelHover}
                color={active ? '#f87171' : CHAT_THEME.textSecondary}
                border={`1.5px solid ${active ? 'rgba(239,68,68,0.35)' : CHAT_THEME.panelBorder}`}
                _hover={{ bg: active ? 'rgba(239,68,68,0.22)' : CHAT_THEME.panelActive, color: active ? '#f87171' : CHAT_THEME.textPrimary }}
                onClick={toggle} transition="all 0.15s"
                leftIcon={<Text fontSize="11px">{icon}</Text>}>
                {label}
              </Button>
            ))}
          </HStack>

          <HStack spacing={3}>
            <Text fontSize="12px" color={CHAT_THEME.textTertiary}>
              {modelLabel ? `Модель: ${modelLabel}` : 'Модель: Auto'}
            </Text>
            {!isAuthenticated && (
              <Text fontSize="12px" color={CHAT_THEME.textTertiary}>
                {remainingRequests} запросов
              </Text>
            )}
          </HStack>
        </HStack>
      </Box>
    </Box>
  );
});

export default React.memo(ChatComposerPanel);
