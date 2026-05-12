import { request } from './request';
import { mapJobDto } from './dtoMappers';

export const startJob = ({ fileId, type = 'CHAT' } = {}, options = {}) =>
  request({
    method: 'post',
    url: '/api/jobs/v1/start',
    data: { file_id: fileId, type },
    ...options,
  }, mapJobDto);

export const fetchJobResult = (jobId, { signal } = {}) =>
  request({ method: 'get', url: `/api/jobs/v1/result/${jobId}`, signal }, mapJobDto);

export const getTaskStatus = (taskId, { signal } = {}) =>
  request({ method: 'get', url: `/api/jobs/v1/task/${taskId}/status`, signal });

export const cancelTask = (taskId, { signal } = {}) =>
  request({ method: 'post', url: `/api/jobs/v1/task/${taskId}/cancel`, data: null, signal });
