import { useCallback } from 'react';

export function useChatSideEffects({ toast, navigate }) {
  const notify = useCallback((options) => {
    toast(options);
  }, [toast]);

  const saveSessionUserId = useCallback((userId) => {
    if (typeof window === 'undefined' || !userId) {
      return;
    }
    window.sessionStorage.setItem('user_id', userId);
  }, []);

  const goToThread = useCallback((threadId, options) => {
    navigate(`/chat/${threadId}`, options);
  }, [navigate]);

  return {
    notify,
    saveSessionUserId,
    goToThread,
  };
}
