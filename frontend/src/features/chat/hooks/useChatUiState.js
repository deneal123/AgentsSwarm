import { useCallback, useMemo } from 'react';
import { CHAT_ACTIONS, useChatStateContainer } from '../model/chatStateContainer';

export const useChatUiState = (externalContainer = null) => {
  const container = externalContainer || useChatStateContainer();
  const { state, dispatch } = container;

  const setLoading = useCallback((value) => dispatch({ type: CHAT_ACTIONS.SET_LOADING, payload: value }), [dispatch]);
  const setError = useCallback((value) => dispatch({ type: CHAT_ACTIONS.SET_ERROR, payload: value }), [dispatch]);
  const setConnectionState = useCallback((value) => dispatch({ type: CHAT_ACTIONS.SET_CONNECTION_STATE, payload: value }), [dispatch]);

  const clearError = useCallback(() => dispatch({ type: CHAT_ACTIONS.CLEAR_ERROR }), [dispatch]);

  const scopedState = useMemo(() => ({ loading: state.loading, error: state.error, connectionState: state.connectionState }), [state.connectionState, state.error, state.loading]);
  const actions = useMemo(() => ({ setLoading, setError, clearError, setConnectionState }), [clearError]);

  return { state: scopedState, actions, container };
};
