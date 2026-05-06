import React, { createContext, useContext, useMemo } from 'react';
import { useChatSessionState } from '../hooks/useChatSessionState';
import { useChatMessagesState } from '../hooks/useChatMessagesState';
import { useChatUiState } from '../hooks/useChatUiState';
import { useChatSideEffects } from '../hooks/useChatSideEffects';

const ChatContext = createContext(null);

// Типы действий для reducer
export const CHAT_ACTIONS = {
  // Сообщения
  ADD_MESSAGE: 'ADD_MESSAGE',
  UPDATE_MESSAGE: 'UPDATE_MESSAGE',
  REMOVE_MESSAGE: 'REMOVE_MESSAGE',
  CLEAR_MESSAGES: 'CLEAR_MESSAGES',

  // Attachments
  ADD_ATTACHMENT: 'ADD_ATTACHMENT',
  REMOVE_ATTACHMENT: 'REMOVE_ATTACHMENT',
  CLEAR_ATTACHMENTS: 'CLEAR_ATTACHMENTS',

  // Typing indicators
  SET_TYPING: 'SET_TYPING',
  CLEAR_TYPING: 'CLEAR_TYPING',

  // Jobs
  SET_CURRENT_JOB: 'SET_CURRENT_JOB',
  UPDATE_JOB_PROGRESS: 'UPDATE_JOB_PROGRESS',
  CLEAR_JOB: 'CLEAR_JOB',

  // UI state
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',

  // Connection
  SET_CONNECTION_STATE: 'SET_CONNECTION_STATE',
};

// Начальное состояние
export const initialState = {
  messages: [],
  attachments: [],
  typingUsers: new Set(),
  currentJob: null,
  loading: false,
  error: null,
  connectionState: 'disconnected',
};

// Reducer для управления состоянием
export function chatReducer(state, action) {
  switch (action.type) {
    case CHAT_ACTIONS.ADD_MESSAGE:
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };

    case CHAT_ACTIONS.UPDATE_MESSAGE:
      return {
        ...state,
        messages: state.messages.map(msg =>
          msg.id === action.payload.id ? { ...msg, ...action.payload } : msg
        ),
      };

    case CHAT_ACTIONS.REMOVE_MESSAGE:
      return {
        ...state,
        messages: state.messages.filter(msg => msg.id !== action.payload),
      };

    case CHAT_ACTIONS.CLEAR_MESSAGES:
      return {
        ...state,
        messages: [],
      };

    case CHAT_ACTIONS.ADD_ATTACHMENT:
      return {
        ...state,
        attachments: [...state.attachments, action.payload],
      };

    case CHAT_ACTIONS.REMOVE_ATTACHMENT:
      return {
        ...state,
        attachments: state.attachments.filter(att => att.id !== action.payload),
      };

    case CHAT_ACTIONS.CLEAR_ATTACHMENTS:
      return {
        ...state,
        attachments: [],
      };

    case CHAT_ACTIONS.SET_TYPING:
      return {
        ...state,
        typingUsers: new Set([...state.typingUsers, action.payload]),
      };

    case CHAT_ACTIONS.CLEAR_TYPING:
      const newTypingUsers = new Set(state.typingUsers);
      newTypingUsers.delete(action.payload);
      return {
        ...state,
        typingUsers: newTypingUsers,
      };

    case CHAT_ACTIONS.SET_CURRENT_JOB:
      return {
        ...state,
        currentJob: action.payload,
      };

    case CHAT_ACTIONS.UPDATE_JOB_PROGRESS:
      return {
        ...state,
        currentJob: state.currentJob ? { ...state.currentJob, ...action.payload } : null,
      };

    case CHAT_ACTIONS.CLEAR_JOB:
      return {
        ...state,
        currentJob: null,
      };

    case CHAT_ACTIONS.SET_LOADING:
      return {
        ...state,
        loading: action.payload,
      };

    case CHAT_ACTIONS.SET_ERROR:
      return {
        ...state,
        error: action.payload,
      };

    case CHAT_ACTIONS.CLEAR_ERROR:
      return {
        ...state,
        error: null,
      };

    case CHAT_ACTIONS.SET_CONNECTION_STATE:
      return {
        ...state,
        connectionState: action.payload,
      };

    default:
      return state;
  }
}

// Chat Provider компонент
export function ChatProvider({ threadId, children }) {
  const sessionState = useChatSessionState();
  const messagesState = useChatMessagesState();
  const uiState = useChatUiState();

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
