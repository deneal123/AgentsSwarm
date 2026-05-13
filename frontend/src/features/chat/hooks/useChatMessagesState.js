import { useCallback, useMemo } from 'react';
import { CHAT_ACTIONS, useChatStateContainer } from '../model/chatStateContainer';

export const useChatMessagesState = (externalContainer = null) => {
  const internalContainer = useChatStateContainer();
  const container = externalContainer ?? internalContainer;
  const { state, dispatch } = container;

  const addMessage = useCallback((message) => {
    dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: message });
  }, [dispatch]);

  const updateMessage = useCallback((id, updates) => {
    dispatch({ type: CHAT_ACTIONS.UPDATE_MESSAGE, payload: { id, ...updates } });
  }, [dispatch]);

  const removeMessage = useCallback((id) => {
    dispatch({ type: CHAT_ACTIONS.REMOVE_MESSAGE, payload: id });
  }, [dispatch]);

  const clearMessages = useCallback(() => {
    dispatch({ type: CHAT_ACTIONS.CLEAR_MESSAGES });
  }, [dispatch]);

  const setCurrentJob = useCallback((job) => {
    dispatch({ type: CHAT_ACTIONS.SET_CURRENT_JOB, payload: job });
  }, [dispatch]);

  const scopedState = useMemo(() => ({ messages: state.messages, currentJob: state.currentJob }), [state.currentJob, state.messages]);
  const actions = useMemo(() => ({ addMessage, updateMessage, removeMessage, clearMessages, setCurrentJob }), [addMessage, updateMessage, removeMessage, clearMessages, setCurrentJob]);

  return { state: scopedState, actions, container };
};
