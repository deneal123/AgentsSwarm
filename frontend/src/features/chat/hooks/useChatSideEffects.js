import { useCallback } from 'react';
import { useAppToast } from '@shared/hooks/useAppToast';

export function useChatSideEffects({ navigate }) {
  const appToast = useAppToast();
  const notify = useCallback((options) => {
    appToast(options);
  }, [appToast]);

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
