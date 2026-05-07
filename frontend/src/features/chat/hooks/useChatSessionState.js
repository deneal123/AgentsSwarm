import { useCallback, useMemo } from 'react';
import { CHAT_ACTIONS, useChatStateContainer } from '../model/chatStateContainer';

export const useChatSessionState = (externalContainer = null) => {
  const container = externalContainer || useChatStateContainer();
  const { state, dispatch } = container;

  const addAttachment = useCallback((attachment) => {
    dispatch({ type: CHAT_ACTIONS.ADD_ATTACHMENT, payload: attachment });
  }, [dispatch]);

  const removeAttachment = useCallback((id) => {
    dispatch({ type: CHAT_ACTIONS.REMOVE_ATTACHMENT, payload: id });
  }, [dispatch]);

  const clearAttachments = useCallback(() => {
    dispatch({ type: CHAT_ACTIONS.CLEAR_ATTACHMENTS });
  }, [dispatch]);

  const setTyping = useCallback((userId) => {
    dispatch({ type: CHAT_ACTIONS.SET_TYPING, payload: userId });
  }, [dispatch]);

  const clearTyping = useCallback((userId) => {
    dispatch({ type: CHAT_ACTIONS.CLEAR_TYPING, payload: userId });
  }, [dispatch]);

  const scopedState = useMemo(() => ({ attachments: state.attachments, typingUsers: state.typingUsers }), [state.attachments, state.typingUsers]);
  const actions = useMemo(() => ({ addAttachment, removeAttachment, clearAttachments, setTyping, clearTyping }), [addAttachment, removeAttachment, clearAttachments, setTyping, clearTyping]);

  return { state: scopedState, actions, container };
};
