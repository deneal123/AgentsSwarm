import { useMemo } from 'react';
import { useWebSocketChat } from '../model/useWebSocketChat';

export function useChatTransport({ threadId, callbacks, isAuthenticated }) {
  const wsCallbacks = useMemo(() => ({
    onMessage: () => {},
    ...callbacks,
  }), [callbacks]);

  const transport = useWebSocketChat(threadId, wsCallbacks, isAuthenticated);

  return {
    isConnected: transport.isConnected,
    connectionState: transport.connectionState,
    currentJob: transport.currentJob,
    agentStatus: transport.agentStatus,
    sendMessage: transport.sendMessage,
    cancelJob: transport.cancelJob,
    useWebSocket: transport.isConnected && transport.connectionState === 'connected',
  };
}
