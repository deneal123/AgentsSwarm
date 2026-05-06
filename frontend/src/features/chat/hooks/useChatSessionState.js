import { useCallback, useMemo, useState } from 'react';

const initialSessionState = {
  attachments: [],
  typingUsers: new Set(),
};

export const useChatSessionState = () => {
  const [attachments, setAttachments] = useState(initialSessionState.attachments);
  const [typingUsers, setTypingUsers] = useState(initialSessionState.typingUsers);

  const addAttachment = useCallback((attachment) => {
    setAttachments((prev) => [...prev, attachment]);
  }, []);

  const removeAttachment = useCallback((id) => {
    setAttachments((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachments([]);
  }, []);

  const setTyping = useCallback((userId) => {
    setTypingUsers((prev) => new Set([...prev, userId]));
  }, []);

  const clearTyping = useCallback((userId) => {
    setTypingUsers((prev) => {
      const next = new Set(prev);
      next.delete(userId);
      return next;
    });
  }, []);

  const state = useMemo(() => ({ attachments, typingUsers }), [attachments, typingUsers]);
  const actions = useMemo(() => ({ addAttachment, removeAttachment, clearAttachments, setTyping, clearTyping }), [addAttachment, removeAttachment, clearAttachments, setTyping, clearTyping]);

  return { state, actions };
};
