import { useCallback, useMemo } from 'react';
import { CHAT_ACTIONS, useChatStateContainer } from '../model/chatStateContainer';

export function useChatDomainState() {
  const container = useChatStateContainer();
  const { state, dispatch } = container;

  const setLoading = useCallback((value) => dispatch({ type: CHAT_ACTIONS.SET_LOADING, payload: value }), [dispatch]);
  const setError = useCallback((value) => dispatch({ type: CHAT_ACTIONS.SET_ERROR, payload: value }), [dispatch]);
  const clearError = useCallback(() => dispatch({ type: CHAT_ACTIONS.CLEAR_ERROR }), [dispatch]);
  const setCurrentJob = useCallback((value) => dispatch({ type: CHAT_ACTIONS.SET_CURRENT_JOB, payload: value }), [dispatch]);
  const clearCurrentJob = useCallback(() => dispatch({ type: CHAT_ACTIONS.CLEAR_JOB }), [dispatch]);
  const addMessage = useCallback((message) => dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: message }), [dispatch]);
  const clearMessages = useCallback(() => dispatch({ type: CHAT_ACTIONS.CLEAR_MESSAGES }), [dispatch]);
  const replaceMessages = useCallback((items) => {
    dispatch({ type: CHAT_ACTIONS.CLEAR_MESSAGES });
    items.forEach((item) => dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: item }));
  }, [dispatch]);
  const updateLastAgentChunk = useCallback((chunk, metadata) => {
    dispatch({ type: CHAT_ACTIONS.STREAM_APPEND_CHUNK, payload: { chunk, metadata } });
  }, [dispatch]);
  const completeLastAgentMessage = useCallback(() => dispatch({ type: CHAT_ACTIONS.STREAM_COMPLETE_LAST_AGENT }), [dispatch]);
  const finalizeStreamWithContent = useCallback((content, metadata, file_url) => dispatch({ type: CHAT_ACTIONS.STREAM_FINALIZE_WITH_CONTENT, payload: { content, metadata, file_url } }), [dispatch]);
  const addTraceSession = useCallback((session) => dispatch({ type: CHAT_ACTIONS.TRACE_START_SESSION, payload: session }), [dispatch]);
  const appendTrace = useCallback((sessionId, event) => dispatch({ type: CHAT_ACTIONS.TRACE_APPEND_EVENT, payload: { sessionId, event } }), [dispatch]);
  const finalizeTrace = useCallback((sessionId, status) => dispatch({ type: CHAT_ACTIONS.TRACE_FINALIZE_SESSION, payload: { sessionId, status } }), [dispatch]);

  const domainState = useMemo(() => ({
    messages: state.messages,
    currentJob: state.currentJob,
    loading: state.loading,
    error: state.error,
    traceSessions: state.traceSessions,
  }), [state.currentJob, state.error, state.loading, state.messages, state.traceSessions]);

  const actions = useMemo(() => ({ setLoading, setError, clearError, setCurrentJob, clearCurrentJob, addMessage, clearMessages, replaceMessages, updateLastAgentChunk, completeLastAgentMessage, finalizeStreamWithContent, addTraceSession, appendTrace, finalizeTrace }), [addMessage, addTraceSession, appendTrace, clearCurrentJob, clearError, clearMessages, completeLastAgentMessage, finalizeStreamWithContent, finalizeTrace, replaceMessages, setCurrentJob, setError, setLoading, updateLastAgentChunk]);

  return { state: domainState, actions, container };
}
