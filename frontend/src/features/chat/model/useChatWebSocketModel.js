import { useMemo } from 'react';
import { useWebSocketChat } from './useWebSocketChat';

export function useChatWebSocketModel({ threadId, callbacks, isAuthenticated }) {
  const wsState = useWebSocketChat(threadId, callbacks, isAuthenticated);

  return useMemo(
    () => ({
      ...wsState,
      isWsReady: wsState.isConnected,
      wsConnectionState: wsState.connectionState,
      wsMessages: wsState.messages,
      wsCurrentJob: wsState.currentJob,
    }),
    [wsState],
  );
}
