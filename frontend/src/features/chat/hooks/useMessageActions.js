import { useCallback } from 'react';

export function useMessageActions({ messages, actions, handleSendMessageRef }) {
  const copyMessage = useCallback((text) => {
    if (!text) return;
    navigator.clipboard?.writeText(text).catch(() => {});
  }, []);

  const regenerateMessage = useCallback((messageId) => {
    const idx = messages.findIndex((message) => message.id === messageId);
    if (idx === -1) return;

    let userIdx = -1;
    for (let i = idx - 1; i >= 0; i -= 1) {
      if (messages[i]?.type === 'user' && messages[i]?.content) {
        userIdx = i;
        break;
      }
    }
    if (userIdx === -1) return;

    const userMessage = messages[userIdx];
    actions.truncateAfter(userIdx + 1);
    handleSendMessageRef.current?.(userMessage.content, {
      skipUserAppend: true,
      anchorMessageId: userMessage.id,
    });
  }, [actions, handleSendMessageRef, messages]);

  return {
    copyMessage,
    regenerateMessage,
  };
}
