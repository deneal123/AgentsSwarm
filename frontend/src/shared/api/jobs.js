import { request } from './request';
import { mapJobDto } from './dtoMappers';

export const startJob = ({ datasetId, fileId, mode = 'TRAINING', type = 'TRAIN', targetColumn, useAi = false, taskType = 'classification' } = {}, options = {}) => {
  const datasetIdentifier = datasetId ?? fileId;
  return request({
    method: 'post',
    url: '/api/jobs/v1/start',
    data: {
      dataset_id: datasetIdentifier,
      file_id: fileId ?? datasetIdentifier,
      target_column: targetColumn?.trim() || undefined,
      mode,
      type,
      use_ai: useAi,
      task_type: taskType,
    },
    ...options,
  }, mapJobDto);
};

export const fetchJobResult = (jobId, { signal } = {}) => request({ method: 'get', url: `/api/jobs/v1/result/${jobId}`, signal }, mapJobDto);
export const getTaskStatus = (taskId, { signal } = {}) => request({ method: 'get', url: `/api/jobs/v1/task/${taskId}/status`, signal }, mapJobDto);
export const cancelTask = (taskId, { signal } = {}) => request({ method: 'post', url: `/api/jobs/v1/task/${taskId}/cancel`, data: null, signal }, mapJobDto);
