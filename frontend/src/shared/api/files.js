import { request } from './request';

export const fetchAvailableModes = (options = {}) =>
  request({ method: 'get', url: '/api/service/files/v1/modes', ...options });

export const fetchUserFiles = (mode = 'CHAT', options = {}) =>
  request({ method: 'get', url: `/api/service/files/v1/fetch/${mode}`, ...options });

export const uploadFile = (mode = 'CHAT', file, onProgress, options = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  return request({
    method: 'post',
    url: `/api/service/files/v1/upload/${mode}`,
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / e.total)),
    timeout: 60000,
    ...options,
  });
};

export const deleteFile = (fileId, options = {}) =>
  request({ method: 'delete', url: `/api/service/files/v1/delete/${fileId}`, ...options });

export const presignUpload = (mode = 'CHAT', fileName, expirySec = 3600, options = {}) =>
  request({ method: 'post', url: `/api/service/files/v1/presign/${mode}`, data: { filename: fileName, expiry_sec: expirySec }, ...options });

export const confirmUploadCallback = (fileId, mode, fileKey, options = {}) =>
  request({ method: 'post', url: `/api/service/files/v1/${fileId}/callback`, data: { mode, file_key: fileKey }, ...options });

export const getFileDetail = (fileId, options = {}) =>
  request({ method: 'get', url: `/api/service/files/v1/${fileId}`, ...options });
