import client from "./client";

/**
 * Start a training job.
 *
 * @param {Object} options
 * @param {string} [options.datasetId] - Dataset UUID
 * @param {string} [options.fileId] - Legacy file UUID (use datasetId instead)
 * @param {string} [options.mode="TRAINING"] - Service mode
 * @param {string} [options.type="TRAIN"] - Service type
 * @param {string} [options.targetColumn] - Target column name
 * @param {boolean} [options.useAi=false] - Use AI agents for processing
 * @param {string} [options.taskType="classification"] - ML task type: classification or regression
 * @returns {Promise<Object>} Job response with job_id, status, celery_task_id, etc.
 */
export async function startJob({
  datasetId,
  fileId,
  mode = "TRAINING",
  type = "TRAIN",
  targetColumn,
  useAi = false,
  taskType = "classification",
} = {}) {
  const datasetIdentifier = datasetId ?? fileId;
  const payload = {
    dataset_id: datasetIdentifier,
    file_id: fileId ?? datasetIdentifier,
    target_column: targetColumn?.trim() || undefined,
    mode,
    type,
    use_ai: useAi,
    task_type: taskType,
  };
  const res = await client.post("/api/jobs/v1/start", payload);
  return res.data;
}

/**
 * Get job result by job ID.
 *
 * @param {string} jobId - Job UUID
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal] - Abort signal
 * @returns {Promise<Object>} Job response with status, metrics, model_url, etc.
 */
export async function fetchJobResult(jobId, { signal } = {}) {
  const res = await client.get(`/api/jobs/v1/result/${jobId}`, { signal });
  return res.data;
}

/**
 * Get Celery task status for async tracking.
 *
 * @param {string} taskId - Celery task ID
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal] - Abort signal
 * @returns {Promise<Object>} Task status: { task_id, state, progress, status, result, error }
 */
export async function getTaskStatus(taskId, { signal } = {}) {
  const res = await client.get(`/api/jobs/v1/task/${taskId}/status`, { signal });
  return res.data;
}

/**
 * Cancel a running Celery task.
 *
 * @param {string} taskId - Celery task ID
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal] - Abort signal
 * @returns {Promise<Object>} Response with { task_id, cancelled }
 */
export async function cancelTask(taskId, { signal } = {}) {
  const res = await client.post(`/api/jobs/v1/task/${taskId}/cancel`, null, { signal });
  return res.data;
}
