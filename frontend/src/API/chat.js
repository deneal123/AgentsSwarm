import client from "./client";

/**
 * API функции для работы с чат-агентами
 */

/**
 * Создание нового чат-треда
 * @param {string} [userId] - ID пользователя (опционально для гостей)
 * @returns {Promise<Object>} Объект с thread_id
 */
export async function createChatThread(userId = null) {
  const payload = userId ? { user_id: userId } : {};
  const response = await client.post('/api/chats/', payload);
  return response.data;
}

/**
 * Отправка сообщения в чат-агент
 * @param {string} threadId - ID чат-треда
 * @param {string} message - Текст сообщения
 * @param {string} [userId] - ID пользователя (опционально)
 * @returns {Promise<Object>} Ответ с reply и metadata
 */
export async function sendChatMessage(
  threadId,
  message,
  userId = null,
  model = null,
  inputType = null,
  options = {}
) {
  const {
    webSearch = false,
    deepResearch = false,
    fileContext = '',
    fileIds = [],
    routeOverride = null,
  } = options || {};

  const payload = {
    text: message.trim(),
    ...(userId && { user_id: userId }),
    ...(model && { model }),
    ...(inputType && { input_type: inputType }),
    ...(webSearch && { web_search: true }),
    ...(deepResearch && { deep_research: true }),
    ...(fileContext && { file_context: fileContext }),
    ...(Array.isArray(fileIds) && fileIds.length && { file_ids: fileIds }),
    ...(routeOverride && { route_override: routeOverride }),
  };

  const response = await client.post(`/api/chats/${threadId}/message`, payload);
  return response.data;
}

/**
 * Получение доступных моделей MWS GPT
 * @returns {Promise<Array<string>>} Массив id моделей
 */
export async function getChatModels() {
  const response = await client.get('/api/chats/models');
  return response.data?.models || [];
}

/**
 * Получение истории чата
 * @param {string} threadId - ID чат-треда
 * @param {number} [limit=50] - Максимальное количество сообщений
 * @param {string} [before] - Курсор для пагинации
 * @returns {Promise<Object>} История чата с messages
 */
export async function getChatHistory(threadId, limit = 50) {
  const params = new URLSearchParams({ per_page: limit.toString(), page: '1' });
  const response = await client.get(`/api/chats/${threadId}?${params}`);
  return response.data;
}

/**
 * Получение списка чатов пользователя
 * @param {string} userId - ID пользователя
 * @param {number} [limit=20] - Количество чатов
 * @param {string} [before] - Курсор для пагинации
 * @returns {Promise<Object>} Список чатов
 */
export async function getUserChats(userId, limit = 20) {
  const params = new URLSearchParams({ per_page: limit.toString(), page: '1' });
  if (userId != null) params.append('user_id', userId);

  const response = await client.get(`/api/chats/?${params}`);
  return response.data;
}

/**
 * Удаление чат-треда
 * @param {string} threadId - ID чат-треда
 * @param {string} userId - ID пользователя (для проверки прав)
 * @returns {Promise<Object>} Подтверждение удаления
 */
export async function deleteChatThread(threadId, userId) {
  const response = await client.delete(`/api/chats/${threadId}`, {
    data: { user_id: userId }
  });
  return response.data;
}

/**
 * Переименование чат-треда
 * @param {string} threadId - ID чат-треда
 * @param {string} title - Новое название
 * @param {string} userId - ID пользователя
 * @returns {Promise<Object>} Обновленный чат
 */
export async function renameChatThread(threadId, title, userId) {
  const response = await client.patch(`/api/chats/${threadId}`, {
    title: title.trim(),
    user_id: userId
  });
  return response.data;
}

/**
 * Получение информации о чате
 * @param {string} threadId - ID чат-треда
 * @returns {Promise<Object>} Информация о чате
 */
export async function getChatInfo(threadId) {
  const response = await client.get(`/api/chats/${threadId}/info`);
  return response.data;
}


/**
 * Получение статистики использования чатов
 * @param {string} userId - ID пользователя
 * @param {string} period - Период ('day', 'week', 'month')
 * @returns {Promise<Object>} Статистика использования
 */
export async function getChatStats(userId, period = 'month') {
  const response = await client.get('/api/chats/stats', {
    params: { user_id: userId, period }
  });
  return response.data;
}

/**
 * Загрузка файла в чат
 * @param {string} threadId - ID чат-треда
 * @param {File} file - Файл для загрузки
 * @param {Function} [onProgress] - Callback для отслеживания прогресса
 * @returns {Promise<Object>} Информация о загруженном файле
 */
export async function uploadChatFile(threadId, file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);

  const response = await client.post('/api/chats/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      }
    },
  });

  const data = response.data || {};
  const extractedText = data.extracted_text || '';

  return {
    ...data,
    file_id: data.file_id || `file_${Date.now()}_${Math.random()}`,
    download_url: data.download_url || data.file_url || null,
    file_context: extractedText,
    content_preview: extractedText,
  };
}

/**
 * Создание presigned URL для загрузки файла
 * @param {string} fileName - Имя файла
 * @param {string} contentType - MIME тип файла
 * @param {string} threadId - ID чат-треда
 * @returns {Promise<Object>} Presigned URL данные
 */
export async function createFileUploadUrl(fileName, contentType, threadId) {
  const response = await client.post('/api/files/v1/presign/chat', {
    filename: fileName,
    content_type: contentType,
    thread_id: threadId
  });
  return response.data;
}

/**
 * Получение деталей сообщения
 * @param {string} threadId - ID чат-треда
 * @param {string} messageId - ID сообщения
 * @returns {Promise<Object>} Детали сообщения
 */
export async function getMessageDetails(threadId, messageId) {
  const response = await client.get(`/api/chats/${threadId}/messages/${messageId}`);
  return response.data;
}

/**
 * Добавление реакции к сообщению
 * @param {string} threadId - ID чат-треда
 * @param {string} messageId - ID сообщения
 * @param {string} reaction - Тип реакции (like, dislike, etc.)
 * @param {string} [userId] - ID пользователя
 * @returns {Promise<Object>} Обновленное сообщение
 */
export async function addMessageReaction(threadId, messageId, reaction, userId) {
  const response = await client.post(`/api/chats/${threadId}/messages/${messageId}/reactions`, {
    reaction,
    user_id: userId
  });
  return response.data;
}

/**
 * Удаление реакции с сообщения
 * @param {string} threadId - ID чат-треда
 * @param {string} messageId - ID сообщения
 * @param {string} reaction - Тип реакции для удаления
 * @param {string} [userId] - ID пользователя
 * @returns {Promise<Object>} Обновленное сообщение
 */
export async function removeMessageReaction(threadId, messageId, reaction, userId) {
  const response = await client.delete(`/api/chats/${threadId}/messages/${messageId}/reactions`, {
    data: {
      reaction,
      user_id: userId
    }
  });
  return response.data;
}

/**
 * Поиск по сообщениям в чате
 * @param {string} threadId - ID чат-треда
 * @param {string} query - Поисковый запрос
 * @param {string} [userId] - ID пользователя
 * @param {Object} [options] - Дополнительные опции поиска
 * @returns {Promise<Object>} Результаты поиска
 */
export async function searchChatMessages(threadId, query, userId, options = {}) {
  const params = {
    q: query,
    user_id: userId,
    ...options
  };

  const response = await client.get(`/api/chats/${threadId}/search`, { params });
  return response.data;
}

/**
 * Экспорт истории чата
 * @param {string} threadId - ID чат-треда
 * @param {string} format - Формат экспорта ('json', 'txt', 'pdf')
 * @param {string} [userId] - ID пользователя
 * @returns {Promise<Blob>} Файл с экспортированной историей
 */
export async function exportChatHistory(threadId, format = 'json', userId) {
  const response = await client.get(`/api/chats/${threadId}/export`, {
    params: { format, user_id: userId },
    responseType: 'blob'
  });
  return response.data;
}

/**
 * Отправка отзыва о сообщении
 * @param {string} threadId - ID чат-треда
 * @param {string} messageId - ID сообщения
 * @param {Object} feedback - Объект с отзывом
 * @param {string} [userId] - ID пользователя
 * @returns {Promise<Object>} Подтверждение отправки отзыва
 */
export async function sendMessageFeedback(threadId, messageId, feedback, userId) {
  const response = await client.post(`/api/chats/${threadId}/messages/${messageId}/feedback`, {
    feedback,
    user_id: userId
  });
  return response.data;
}

/**
 * Получение предложений для автодополнения
 * @param {string} threadId - ID чат-треда
 * @param {string} prefix - Префикс для автодополнения
 * @returns {Promise<Array>} Массив предложений
 */
export async function getAutocompleteSuggestions(threadId, prefix) {
  const response = await client.get(`/api/chats/${threadId}/autocomplete`, {
    params: { prefix }
  });
  return response.data;
}

// ==================== Memory API ====================

/**
 * Получение фактов из памяти пользователя
 * @param {string} userId - ID пользователя
 * @returns {Promise<Object>} Объект с facts и context_text
 */
export async function getUserMemory(userId) {
  const response = await client.get(`/api/memory/${userId}`);
  return response.data;
}

/**
 * Добавление факта в память пользователя
 */
export async function addMemoryFact(userId, factType, factKey, factValue) {
  const response = await client.post(`/api/memory/${userId}/facts`, {
    user_id: userId,
    fact_type: factType,
    fact_key: factKey,
    fact_value: factValue,
  });
  return response.data;
}

/**
 * Удаление факта из памяти
 */
export async function deleteMemoryFact(userId, factId) {
  await client.delete(`/api/memory/${userId}/facts/${factId}`);
}

/**
 * Поиск по памяти пользователя
 */
export async function searchMemory(userId, query) {
  const response = await client.get(`/api/memory/${userId}/search`, {
    params: { q: query }
  });
  return response.data;
}

// ==================== File Upload ====================

/**
 * Загрузка файла и извлечение текста
 */
export async function uploadFileForChat(file, threadId = '') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);

  const response = await client.post('/api/chats/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
  return response.data;
}

// ==================== Web Search ====================

/**
 * Веб-поиск
 */
export async function webSearch(query, numResults = 5) {
  const response = await client.post('/api/chats/web-search', null, {
    params: { q: query, num_results: numResults }
  });
  return response.data;
}

/**
 * Парсинг URL
 */
export async function parseUrl(url) {
  const response = await client.post('/api/chats/parse-url', null, {
    params: { url }
  });
  return response.data;
}
