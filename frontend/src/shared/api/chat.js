import { request } from './request';
import { mapChatUploadResponse, mapModelsResponse } from './dtoMappers';

export const createChatThread = (userId = null, options = {}) =>
  request({ method: 'post', url: '/api/chats/', data: userId ? { user_id: userId } : {}, ...options });

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

export const getChatModels = (options = {}) =>
  request({ method: 'get', url: '/api/chats/models', ...options }, mapModelsResponse);

export const getChatHistory = (threadId, limit = 50, options = {}) =>
  request({ method: 'get', url: `/api/chats/${threadId}`, params: { per_page: limit.toString(), page: '1' }, ...options });

export const getUserChats = (userId, limit = 20, options = {}) =>
  request({ method: 'get', url: '/api/chats/', params: { per_page: limit.toString(), page: '1', ...(userId != null ? { user_id: userId } : {}) }, ...options });

export const deleteChatThread = (threadId, userId, options = {}) =>
  request({ method: 'delete', url: `/api/chats/${threadId}`, data: { user_id: userId }, ...options });

export const uploadChatFile = (file, threadId = '', onProgress, options = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);
  return request(
    { method: 'post', url: '/api/chats/upload', data: formData, headers: { 'Content-Type': 'multipart/form-data' }, onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / e.total)), timeout: 60000, ...options },
    mapChatUploadResponse,
  );
};

export const createFileUploadUrl = (fileName, contentType, mode = 'CHAT', options = {}) =>
  request({ method: 'post', url: `/api/service/files/v1/presign/${mode}`, data: { filename: fileName, content_type: contentType }, ...options });

export const getUserMemory = (userId, options = {}) =>
  request({ method: 'get', url: `/api/memory/${userId}`, ...options });

export const addMemoryFact = (userId, factType, factKey, factValue, options = {}) =>
  request({ method: 'post', url: `/api/memory/${userId}/facts`, data: { user_id: userId, fact_type: factType, fact_key: factKey, fact_value: factValue }, ...options });

export const deleteMemoryFact = (userId, factId, options = {}) =>
  request({ method: 'delete', url: `/api/memory/${userId}/facts/${factId}`, ...options });

export const searchMemory = (userId, query, options = {}) =>
  request({ method: 'get', url: `/api/memory/${userId}/search`, params: { q: query }, ...options });

/** @deprecated Use uploadChatFile */
export const uploadFileForChat = (file, threadId = '', options = {}) =>
  uploadChatFile(file, threadId, undefined, options);

export const webSearch = (query, numResults = 5, options = {}) =>
  request({ method: 'post', url: '/api/chats/web-search', data: null, params: { q: query, num_results: numResults }, ...options });

export const parseUrl = (url, options = {}) =>
  request({ method: 'post', url: '/api/chats/parse-url', data: null, params: { url }, ...options });
