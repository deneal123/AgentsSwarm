import { useCallback, useMemo, useState } from 'react';

export const useChatMessagesState = () => {
  const [messages, setMessages] = useState([]);
  const [currentJob, setCurrentJob] = useState(null);

  const addMessage = useCallback((message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const updateMessage = useCallback((id, updates) => {
    setMessages((prev) => prev.map((item) => (item.id === id ? { ...item, ...updates } : item)));
  }, []);

  const removeMessage = useCallback((id) => {
    setMessages((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const state = useMemo(() => ({ messages, currentJob }), [messages, currentJob]);
  const actions = useMemo(() => ({ addMessage, updateMessage, removeMessage, clearMessages, setCurrentJob }), [addMessage, updateMessage, removeMessage, clearMessages]);

  return { state, actions };
};
