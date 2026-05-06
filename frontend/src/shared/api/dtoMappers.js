export const mapIdentity = (data) => data;

export const mapChatUploadResponse = (data = {}) => {
  const extractedText = data.extracted_text || '';
  return {
    ...data,
    file_id: data.file_id || `file_${Date.now()}_${Math.random()}`,
    download_url: data.download_url || data.file_url || null,
    file_context: extractedText,
    content_preview: extractedText,
  };
};

export const mapModelsResponse = (data = {}) => data?.models || [];
