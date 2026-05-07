import React, { createContext, useContext, useMemo } from 'react';
import { useChatSessionState } from '../hooks/useChatSessionState';
import { useChatMessagesState } from '../hooks/useChatMessagesState';
import { useChatUiState } from '../hooks/useChatUiState';
import { useChatSideEffects } from '../hooks/useChatSideEffects';
import { CHAT_ACTIONS, chatStateReducer, initialChatState, useChatStateContainer } from '../model/chatStateContainer';

const ChatContext = createContext(null);

// Типы действий для reducer
export const initialState = initialChatState;

// Reducer для управления состоянием
export const chatReducer = chatStateReducer;

// Chat Provider компонент
export function ChatProvider({ threadId, children }) {
  const container = useChatStateContainer();
  const sessionState = useChatSessionState(container);
  const messagesState = useChatMessagesState(container);
  const uiState = useChatUiState(container);

  const sideEffects = useChatSideEffects({
    threadId,
    sessionState,
    messagesState,
    uiState,
  });

  const contextValue = useMemo(() => ({
    ...sessionState.state,
    ...messagesState.state,
    ...uiState.state,
    ...sessionState.actions,
    ...messagesState.actions,
    ...uiState.actions,
    ...sideEffects,
    hasAttachments: sessionState.state.attachments.length > 0,
    isTyping: sessionState.state.typingUsers.size > 0,
    messageCount: messagesState.state.messages.length,
    lastMessage: messagesState.state.messages[messagesState.state.messages.length - 1],
  }), [sessionState, messagesState, uiState, sideEffects]);

  return <ChatContext.Provider value={contextValue}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}

export default ChatContext;
