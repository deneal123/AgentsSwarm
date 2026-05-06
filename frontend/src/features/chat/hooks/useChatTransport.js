import { useMemo } from 'react';
import { useChatWebSocketModel } from '../model/useChatWebSocketModel';

export function useChatTransport({ threadId, callbacks, isAuthenticated }) {
  const wsCallbacks = useMemo(() => ({
    onMessage: () => {},
    ...callbacks,
  }), [callbacks]);

  const {
    isConnected,
    connectionState,
    currentJob,
    agentStatus,
    sendMessage,
    cancelJob,
  } = useChatWebSocketModel({ threadId, callbacks: wsCallbacks, isAuthenticated });

  return {
    isConnected,
    connectionState,
    currentJob,
    agentStatus,
    sendMessage,
    cancelJob,
    useWebSocket: isConnected && connectionState === 'connected',
  };
}
