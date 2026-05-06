export const mapIdentity = (data) => data;

export const mapApiError = (error) => ({
  code: error?.code || 'UNKNOWN_ERROR',
  message: error?.message || 'Unexpected error',
  details: error?.details || null,
  status: error?.status || null,
});

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
export const mapProfileDto = (data = {}) => ({ ...data });
export const mapJobDto = (data = {}) => ({ ...data });
export const mapPlatformStatsDto = (data = {}) => ({ ...data });
export const mapFileDownloadDto = (data = {}) => ({ ...data });
