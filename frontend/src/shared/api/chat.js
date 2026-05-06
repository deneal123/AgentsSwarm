import { request } from './request';
import { mapChatUploadResponse, mapIdentity, mapModelsResponse } from './dtoMappers';

export const createChatThread = (userId = null, options = {}) => request({ method: 'post', url: '/api/chats/', data: userId ? { user_id: userId } : {}, ...options });

export const sendChatMessage = (threadId, message, userId = null, model = null, inputType = null, params = {}, options = {}) => {
  const { webSearch = false, deepResearch = false, fileContext = '', fileIds = [], routeOverride = null } = params || {};
  return request({
    method: 'post',
    url: `/api/chats/${threadId}/message`,
    data: {
      text: message.trim(),
      ...(userId && { user_id: userId }),
      ...(model && { model }),
      ...(inputType && { input_type: inputType }),
      ...(webSearch && { web_search: true }),
      ...(deepResearch && { deep_research: true }),
      ...(fileContext && { file_context: fileContext }),
      ...(Array.isArray(fileIds) && fileIds.length && { file_ids: fileIds }),
      ...(routeOverride && { route_override: routeOverride }),
    },
    ...options,
  });
};

export const getChatModels = (options = {}) => request({ method: 'get', url: '/api/chats/models', ...options }, mapModelsResponse);
export const getChatHistory = (threadId, limit = 50, options = {}) => request({ method: 'get', url: `/api/chats/${threadId}`, params: { per_page: limit.toString(), page: '1' }, ...options });
export const getUserChats = (userId, limit = 20, options = {}) => request({ method: 'get', url: '/api/chats/', params: { per_page: limit.toString(), page: '1', ...(userId != null ? { user_id: userId } : {}) }, ...options });
export const deleteChatThread = (threadId, userId, options = {}) => request({ method: 'delete', url: `/api/chats/${threadId}`, data: { user_id: userId }, ...options });
export const renameChatThread = (threadId, title, userId, options = {}) => request({ method: 'patch', url: `/api/chats/${threadId}`, data: { title: title.trim(), user_id: userId }, ...options });
export const getChatInfo = (threadId, options = {}) => request({ method: 'get', url: `/api/chats/${threadId}/info`, ...options });
export const getChatStats = (userId, period = 'month', options = {}) => request({ method: 'get', url: '/api/chats/stats', params: { user_id: userId, period }, ...options });

export const uploadChatFile = (threadId, file, onProgress, options = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);
  return request({ method: 'post', url: '/api/chats/upload', data: formData, headers: { 'Content-Type': 'multipart/form-data' }, onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / e.total)), ...options }, mapChatUploadResponse);
};

export const createFileUploadUrl = (fileName, contentType, threadId, options = {}) => request({ method: 'post', url: '/api/files/v1/presign/chat', data: { filename: fileName, content_type: contentType, thread_id: threadId }, ...options });
export const getMessageDetails = (threadId, messageId, options = {}) => request({ method: 'get', url: `/api/chats/${threadId}/messages/${messageId}`, ...options });
export const addMessageReaction = (threadId, messageId, reaction, userId, options = {}) => request({ method: 'post', url: `/api/chats/${threadId}/messages/${messageId}/reactions`, data: { reaction, user_id: userId }, ...options });
export const removeMessageReaction = (threadId, messageId, reaction, userId, options = {}) => request({ method: 'delete', url: `/api/chats/${threadId}/messages/${messageId}/reactions`, data: { reaction, user_id: userId }, ...options });
export const searchChatMessages = (threadId, query, userId, params = {}, options = {}) => request({ method: 'get', url: `/api/chats/${threadId}/search`, params: { q: query, user_id: userId, ...params }, ...options });
export const exportChatHistory = (threadId, format = 'json', userId, options = {}) => request({ method: 'get', url: `/api/chats/${threadId}/export`, params: { format, user_id: userId }, responseType: 'blob', ...options }, mapIdentity);
export const sendMessageFeedback = (threadId, messageId, feedback, userId, options = {}) => request({ method: 'post', url: `/api/chats/${threadId}/messages/${messageId}/feedback`, data: { feedback, user_id: userId }, ...options });
export const getAutocompleteSuggestions = (threadId, prefix, options = {}) => request({ method: 'get', url: `/api/chats/${threadId}/autocomplete`, params: { prefix }, ...options });

export const getUserMemory = (userId, options = {}) => request({ method: 'get', url: `/api/memory/${userId}`, ...options });
export const addMemoryFact = (userId, factType, factKey, factValue, options = {}) => request({ method: 'post', url: `/api/memory/${userId}/facts`, data: { user_id: userId, fact_type: factType, fact_key: factKey, fact_value: factValue }, ...options });
export const deleteMemoryFact = (userId, factId, options = {}) => request({ method: 'delete', url: `/api/memory/${userId}/facts/${factId}`, ...options });
export const searchMemory = (userId, query, options = {}) => request({ method: 'get', url: `/api/memory/${userId}/search`, params: { q: query }, ...options });

export const uploadFileForChat = (file, threadId = '', options = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);
  return request({ method: 'post', url: '/api/chats/upload', data: formData, headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000, ...options });
};

export const webSearch = (query, numResults = 5, options = {}) => request({ method: 'post', url: '/api/chats/web-search', data: null, params: { q: query, num_results: numResults }, ...options });
export const parseUrl = (url, options = {}) => request({ method: 'post', url: '/api/chats/parse-url', data: null, params: { url }, ...options });
