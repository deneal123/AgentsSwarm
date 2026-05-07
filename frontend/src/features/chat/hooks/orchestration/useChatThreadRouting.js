import { useEffect } from 'react';

export function useChatThreadRouting({ routeThreadId, initialMessage, threadId, navigate }) {
  useEffect(() => {
    if (!routeThreadId && !initialMessage && threadId) {
      navigate(`/chat/${threadId}`, { replace: true });
    }
  }, [routeThreadId, initialMessage, threadId, navigate]);

  return {
    state: {
      hasRouteThreadId: Boolean(routeThreadId),
    },
    actions: {},
  };
}
