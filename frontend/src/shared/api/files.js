import { request } from './request';
import { mapFileDownloadDto } from './dtoMappers';

export const getFileDownloadUrl = (fileId, { expirySec = 3600, signal } = {}) =>
  request({ method: 'get', url: `/api/ml/v1/files/${fileId}/download-url`, params: { expiry_sec: expirySec }, signal }, mapFileDownloadDto);
