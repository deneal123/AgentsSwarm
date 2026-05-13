import { useMemo, useReducer } from 'react';

export const CHAT_ACTIONS = {
  ADD_MESSAGE: 'ADD_MESSAGE', UPDATE_MESSAGE: 'UPDATE_MESSAGE', REMOVE_MESSAGE: 'REMOVE_MESSAGE', CLEAR_MESSAGES: 'CLEAR_MESSAGES',
  ADD_ATTACHMENT: 'ADD_ATTACHMENT', REMOVE_ATTACHMENT: 'REMOVE_ATTACHMENT', CLEAR_ATTACHMENTS: 'CLEAR_ATTACHMENTS',
  SET_TYPING: 'SET_TYPING', CLEAR_TYPING: 'CLEAR_TYPING', SET_CURRENT_JOB: 'SET_CURRENT_JOB', UPDATE_JOB_PROGRESS: 'UPDATE_JOB_PROGRESS', CLEAR_JOB: 'CLEAR_JOB',
  SET_LOADING: 'SET_LOADING', SET_ERROR: 'SET_ERROR', CLEAR_ERROR: 'CLEAR_ERROR', SET_CONNECTION_STATE: 'SET_CONNECTION_STATE',
  SET_SIDEBAR_SEARCH: 'SET_SIDEBAR_SEARCH', SET_SIDEBAR_COLLAPSED: 'SET_SIDEBAR_COLLAPSED', SET_INPUT_VALUE: 'SET_INPUT_VALUE', SET_ATTACHED_FILE: 'SET_ATTACHED_FILE', SET_IS_RECORDING: 'SET_IS_RECORDING',
  TRACE_START_SESSION: 'TRACE_START_SESSION', TRACE_APPEND_EVENT: 'TRACE_APPEND_EVENT', TRACE_FINALIZE_SESSION: 'TRACE_FINALIZE_SESSION', TRACE_RESET: 'TRACE_RESET',
  SOCKET_ERROR: 'SOCKET_ERROR', RECONNECT: 'RECONNECT', CANCEL_GENERATION: 'CANCEL_GENERATION', CLEAR_THREAD: 'CLEAR_THREAD',
  STREAM_APPEND_CHUNK: 'STREAM_APPEND_CHUNK', STREAM_COMPLETE_LAST_AGENT: 'STREAM_COMPLETE_LAST_AGENT', STREAM_FINALIZE_WITH_CONTENT: 'STREAM_FINALIZE_WITH_CONTENT',
};

export const initialChatState = {
  messages: [], attachments: [], typingUsers: new Set(), currentJob: null, loading: false, error: null, connectionState: 'disconnected',
  sidebarSearch: '', isSidebarCollapsed: false, inputValue: '', attachedFile: null, isRecording: false, traceSessions: [], activeTraceSessionId: null, reconnectAttempts: 0,
};

export function chatStateReducer(state, action) { switch (action.type) {
  case CHAT_ACTIONS.ADD_MESSAGE: return { ...state, messages: [...state.messages, action.payload] };
  case CHAT_ACTIONS.UPDATE_MESSAGE: return { ...state, messages: state.messages.map((m) => (m.id === action.payload.id ? { ...m, ...action.payload } : m)) };
  case CHAT_ACTIONS.REMOVE_MESSAGE: return { ...state, messages: state.messages.filter((m) => m.id !== action.payload) };
  case CHAT_ACTIONS.CLEAR_MESSAGES: return { ...state, messages: [] };
  case CHAT_ACTIONS.ADD_ATTACHMENT: return { ...state, attachments: [...state.attachments, action.payload] };
  case CHAT_ACTIONS.REMOVE_ATTACHMENT: return { ...state, attachments: state.attachments.filter((a) => a.id !== action.payload) };
  case CHAT_ACTIONS.CLEAR_ATTACHMENTS: return { ...state, attachments: [] };
  case CHAT_ACTIONS.SET_TYPING: return { ...state, typingUsers: new Set([...state.typingUsers, action.payload]) };
  case CHAT_ACTIONS.CLEAR_TYPING: { const next = new Set(state.typingUsers); next.delete(action.payload); return { ...state, typingUsers: next }; }
  case CHAT_ACTIONS.SET_CURRENT_JOB: return { ...state, currentJob: action.payload };
  case CHAT_ACTIONS.UPDATE_JOB_PROGRESS: return { ...state, currentJob: state.currentJob ? { ...state.currentJob, ...action.payload } : null };
  case CHAT_ACTIONS.CLEAR_JOB: return { ...state, currentJob: null };
  case CHAT_ACTIONS.SET_LOADING: return { ...state, loading: action.payload };
  case CHAT_ACTIONS.SET_ERROR: return { ...state, error: action.payload };
  case CHAT_ACTIONS.CLEAR_ERROR: return { ...state, error: null };
  case CHAT_ACTIONS.SET_CONNECTION_STATE: return { ...state, connectionState: action.payload };
  case CHAT_ACTIONS.SET_SIDEBAR_SEARCH: return { ...state, sidebarSearch: action.payload };
  case CHAT_ACTIONS.SET_SIDEBAR_COLLAPSED: return { ...state, isSidebarCollapsed: action.payload };
  case CHAT_ACTIONS.SET_INPUT_VALUE: return { ...state, inputValue: action.payload };
  case CHAT_ACTIONS.SET_ATTACHED_FILE: return { ...state, attachedFile: action.payload };
  case CHAT_ACTIONS.SET_IS_RECORDING: return { ...state, isRecording: action.payload };
  case CHAT_ACTIONS.TRACE_START_SESSION: return { ...state, traceSessions: [...state.traceSessions, action.payload], activeTraceSessionId: action.payload.id };
  case CHAT_ACTIONS.TRACE_APPEND_EVENT: return { ...state, traceSessions: state.traceSessions.map((s) => s.id === action.payload.sessionId ? { ...s, events: [...s.events, action.payload.event] } : s) };
  case CHAT_ACTIONS.TRACE_FINALIZE_SESSION: return { ...state, traceSessions: state.traceSessions.map((s) => s.id === action.payload.sessionId ? { ...s, status: action.payload.status } : s) };
  case CHAT_ACTIONS.TRACE_RESET: return { ...state, traceSessions: [], activeTraceSessionId: null };
  case CHAT_ACTIONS.SOCKET_ERROR: return { ...state, connectionState: 'error', error: action.payload || 'Socket error', loading: false };
  case CHAT_ACTIONS.RECONNECT: return { ...state, connectionState: 'reconnecting', reconnectAttempts: state.reconnectAttempts + 1 };
  case CHAT_ACTIONS.CANCEL_GENERATION: return { ...state, loading: false, currentJob: null };
  case CHAT_ACTIONS.CLEAR_THREAD: return { ...state, messages: [], traceSessions: [], activeTraceSessionId: null, currentJob: null, error: null };
  case CHAT_ACTIONS.STREAM_APPEND_CHUNK: {
    const chunk = action.payload?.chunk || '';
    const metadata = action.payload?.metadata || {};
    if (!chunk.trim()) return state;
    const last = state.messages[state.messages.length - 1];
    if (last && last.type === 'agent' && !last.complete) {
      const content = `${last.content}${chunk}`;
      return {
        ...state,
        messages: state.messages.map((msg, index) => index === state.messages.length - 1 ? { ...msg, content, typingProgress: Math.min(1, content.length / 1000), metadata: { ...(msg.metadata || {}), ...metadata } } : msg),
      };
    }
    return {
      ...state,
      messages: [...state.messages, { id: `agent_${Date.now()}_${Math.random()}`, type: 'agent', content: chunk, timestamp: new Date().toISOString(), metadata, complete: false, isTyping: true, typingProgress: 0 }],
    };
  }
  case CHAT_ACTIONS.STREAM_COMPLETE_LAST_AGENT:
    return {
      ...state,
      messages: state.messages.map((msg, index) => (index === state.messages.length - 1 && msg.type === 'agent' && msg.isTyping ? { ...msg, isTyping: false, complete: true, typingProgress: 1 } : msg)),
    };
  case CHAT_ACTIONS.STREAM_FINALIZE_WITH_CONTENT: {
    const { content, metadata, file_url } = action.payload;
    const msgs = state.messages;
    const lastIdx = msgs.length - 1;
    if (lastIdx >= 0 && msgs[lastIdx].type === 'agent' && !msgs[lastIdx].complete) {
      return {
        ...state,
        messages: msgs.map((msg, i) => i === lastIdx ? { ...msg, content, metadata: metadata || msg.metadata, file_url: file_url || msg.file_url, complete: true, isTyping: false, typingProgress: 1 } : msg),
      };
    }
    return {
      ...state,
      messages: [...msgs, { id: `agent_${Date.now()}_${Math.random()}`, type: 'agent', content, timestamp: new Date().toISOString(), metadata, file_url, complete: true, isTyping: false, typingProgress: 1 }],
    };
  }
  default: return state;
}}

export function useChatStateContainer() {
  const [state, dispatch] = useReducer(chatStateReducer, initialChatState);
  return useMemo(() => ({ state, dispatch }), [state]);
}
