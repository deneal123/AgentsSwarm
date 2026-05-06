import { useCallback } from "react";

export function useMessageActions({ messages, setMessages, handleSendMessageRef }) {
  const handleCopyMessage = useCallback((text) => {
    if (!text) return;
    try {
      navigator.clipboard?.writeText(text);
    } catch {
      // noop
    }
  }, []);

  const handleRegenerate = useCallback((messageId) => {
    const idx = messages.findIndex((m) => m.id === messageId);
    if (idx === -1) return;
    let userIdx = -1;
    for (let i = idx - 1; i >= 0; i -= 1) {
      if (messages[i]?.type === "user" && messages[i]?.content) {
        userIdx = i;
        break;
      }
    }
    if (userIdx === -1) return;
    const userContent = messages[userIdx].content;
    const anchorMessageId = messages[userIdx].id;
    setMessages((prev) => prev.slice(0, userIdx + 1));
    handleSendMessageRef.current?.(userContent, { skipUserAppend: true, anchorMessageId });
  }, [handleSendMessageRef, messages, setMessages]);

  return { handleCopyMessage, handleRegenerate };
}
