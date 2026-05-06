import React, { createContext, useContext, useReducer, useCallback, useEffect, useMemo } from 'react';
import { useWebSocketChat } from '@hooks/useWebSocketChat';
import { sendChatMessage, uploadChatFile } from '@API/chat';

// Chat Context для управления состоянием чата
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
  const [state, dispatch] = useReducer(chatReducer, initialState);

  // Стабилизируем WebSocket callbacks с useMemo
  const wsCallbacks = useMemo(() => ({
    onMessage: (message) => {
      dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: message });
    },

    onJobUpdate: (jobData) => {
      if (jobData.type === 'job_created') {
        dispatch({ type: CHAT_ACTIONS.SET_CURRENT_JOB, payload: {
          id: jobData.job_id,
          celeryTaskId: jobData.celery_task_id,
          status: 'processing',
          progress: 0,
          type: 'unknown'
        }});
      }
    },

    onComplete: (data) => {
      dispatch({ type: CHAT_ACTIONS.CLEAR_JOB });

      // Добавить финальное сообщение
      if (data.reply) {
        const finalMessage = {
          id: `msg_${Date.now()}_${Math.random()}`,
          type: 'agent',
          content: data.reply,
          timestamp: new Date().toISOString(),
          metadata: data.metadata,
          fileUrl: data.file_url,
          complete: true
        };
        dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: finalMessage });
      }
    },

    onError: (error) => {
      dispatch({ type: CHAT_ACTIONS.SET_ERROR, payload: error.message });
    },

    onConnect: () => {
      dispatch({ type: CHAT_ACTIONS.SET_CONNECTION_STATE, payload: 'connected' });
    },

    onDisconnect: () => {
      dispatch({ type: CHAT_ACTIONS.SET_CONNECTION_STATE, payload: 'disconnected' });
    }
  }), []);

  // WebSocket интеграция
  const {
    isConnected,
    messages: wsMessages,
    currentJob: wsJob,
    sendMessage: wsSendMessage
  } = useWebSocketChat(threadId, wsCallbacks);

  // Синхронизация состояния подключения
  useEffect(() => {
    dispatch({
      type: CHAT_ACTIONS.SET_CONNECTION_STATE,
      payload: isConnected ? 'connected' : 'disconnected'
    });
  }, [isConnected]);

  // Синхронизация сообщений из WebSocket
  useEffect(() => {
    if (wsMessages.length > 0) {
      // Синхронизировать только новые сообщения
      const existingIds = new Set(state.messages.map(m => m.id));
      const newMessages = wsMessages.filter(m => !existingIds.has(m.id));

      newMessages.forEach(message => {
        dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: message });
      });
    }
  }, [wsMessages, state.messages]);

  // Синхронизация job из WebSocket
  useEffect(() => {
    if (wsJob) {
      dispatch({ type: CHAT_ACTIONS.SET_CURRENT_JOB, payload: wsJob });
    }
  }, [wsJob]);

  // Методы для работы с сообщениями
  const addMessage = useCallback((message) => {
    dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: message });
  }, []);

  const updateMessage = useCallback((id, updates) => {
    dispatch({ type: CHAT_ACTIONS.UPDATE_MESSAGE, payload: { id, ...updates } });
  }, []);

  const removeMessage = useCallback((id) => {
    dispatch({ type: CHAT_ACTIONS.REMOVE_MESSAGE, payload: id });
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: CHAT_ACTIONS.CLEAR_MESSAGES });
  }, []);

  // Методы для работы с attachments
  const addAttachment = useCallback((attachment) => {
    dispatch({ type: CHAT_ACTIONS.ADD_ATTACHMENT, payload: attachment });
  }, []);

  const removeAttachment = useCallback((id) => {
    dispatch({ type: CHAT_ACTIONS.REMOVE_ATTACHMENT, payload: id });
  }, []);

  const clearAttachments = useCallback(() => {
    dispatch({ type: CHAT_ACTIONS.CLEAR_ATTACHMENTS });
  }, []);

  // Методы для typing indicators
  const setTyping = useCallback((userId) => {
    dispatch({ type: CHAT_ACTIONS.SET_TYPING, payload: userId });
  }, []);

  const clearTyping = useCallback((userId) => {
    dispatch({ type: CHAT_ACTIONS.CLEAR_TYPING, payload: userId });
  }, []);

  // Методы для отправки сообщений
  const sendMessage = useCallback(async (content, attachments = []) => {
    if (!content.trim() && attachments.length === 0) return;

    dispatch({ type: CHAT_ACTIONS.SET_LOADING, payload: true });
    dispatch({ type: CHAT_ACTIONS.CLEAR_ERROR });

    try {
      // Optimistic update - добавить сообщение сразу
      const optimisticMessage = {
        id: `temp_${Date.now()}`,
        type: 'user',
        content: content.trim(),
        timestamp: new Date().toISOString(),
        attachments: attachments,
        status: 'sending'
      };

      dispatch({ type: CHAT_ACTIONS.ADD_MESSAGE, payload: optimisticMessage });

      // Очистить attachments после отправки
      dispatch({ type: CHAT_ACTIONS.CLEAR_ATTACHMENTS });

      // Отправить через WebSocket (fallback to REST API)
      wsSendMessage(content);

      // Обновить статус на 'sent'
      dispatch({
        type: CHAT_ACTIONS.UPDATE_MESSAGE,
        payload: { id: optimisticMessage.id, status: 'sent' }
      });

    } catch (error) {
      console.error('Failed to send message:', error);

      // Отметить сообщение как failed
      dispatch({
        type: CHAT_ACTIONS.UPDATE_MESSAGE,
        payload: {
          id: `temp_${Date.now()}`,
          status: 'failed',
          error: error.message
        }
      });

      dispatch({ type: CHAT_ACTIONS.SET_ERROR, payload: error.message });
    } finally {
      dispatch({ type: CHAT_ACTIONS.SET_LOADING, payload: false });
    }
  }, [wsSendMessage]);

  // Методы для загрузки файлов
  const uploadFile = useCallback(async (file) => {
    dispatch({ type: CHAT_ACTIONS.SET_LOADING, payload: true });

    try {
      const result = await uploadChatFile(threadId, file, (progress) => {
        // Обновлять прогресс загрузки
        console.log('Upload progress:', progress);
      });

      // Добавить attachment к сообщению
      addAttachment({
        id: result.file_id,
        name: file.name,
        type: file.type,
        size: file.size,
        url: result.download_url,
        uploaded: true
      });

    } catch (error) {
      console.error('Failed to upload file:', error);
      dispatch({ type: CHAT_ACTIONS.SET_ERROR, payload: 'Failed to upload file' });
    } finally {
      dispatch({ type: CHAT_ACTIONS.SET_LOADING, payload: false });
    }
  }, [threadId, addAttachment]);

  // Context value
  const contextValue = {
    // State
    ...state,

    // Methods
    addMessage,
    updateMessage,
    removeMessage,
    clearMessages,
    addAttachment,
    removeAttachment,
    clearAttachments,
    setTyping,
    clearTyping,
    sendMessage,
    uploadFile,

    // Computed properties
    hasAttachments: state.attachments.length > 0,
    isTyping: state.typingUsers.size > 0,
    messageCount: state.messages.length,
    lastMessage: state.messages[state.messages.length - 1],
  };

  return (
    <ChatContext.Provider value={contextValue}>
      {children}
    </ChatContext.Provider>
  );
}

// Hook для использования Chat Context
export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}

export default ChatContext;
