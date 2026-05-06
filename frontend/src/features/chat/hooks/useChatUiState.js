import { useCallback, useMemo, useState } from 'react';

export const useChatUiState = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [connectionState, setConnectionState] = useState('disconnected');

  const clearError = useCallback(() => setError(null), []);

  const state = useMemo(() => ({ loading, error, connectionState }), [loading, error, connectionState]);
  const actions = useMemo(() => ({ setLoading, setError, clearError, setConnectionState }), [clearError]);

  return { state, actions };
};
