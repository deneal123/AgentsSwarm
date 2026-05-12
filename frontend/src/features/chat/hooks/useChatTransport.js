import { useMemo } from 'react';
import { useWebSocketChat } from '../model/useWebSocketChat';

export function useChatTransport({ threadId, callbacks }) {
  const wsCallbacks = useMemo(() => ({
    onMessage: () => {},
    ...callbacks,
  }), [callbacks]);

  const transport = useWebSocketChat(threadId, wsCallbacks);

  return {
    isConnected: transport.isConnected,
    connectionState: transport.connectionState,
    currentJob: transport.currentJob,
    sendMessage: transport.sendMessage,
    cancelJob: transport.cancelJob,
    useWebSocket: transport.isConnected && transport.connectionState === 'connected',
  };
}
