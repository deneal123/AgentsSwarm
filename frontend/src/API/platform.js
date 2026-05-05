import apiClient from "./client";

/**
 * Получить публичную статистику платформы (без авторизации)
 * @param {{ signal?: AbortSignal }} options
 * @returns {Promise<{
 *   total_users: number,
 *   total_datasets: number,
 *   total_training_runs: number,
 *   total_artifacts: number,
 *   avg_accuracy: number | null,
 *   avg_r2: number | null,
 *   best_accuracy: number | null,
 *   best_r2: number | null
 * }>}
 */
export async function getPlatformStats({ signal } = {}) {
  const response = await apiClient.get("/api/ml/v1/platform/stats", { signal });
  return response.data;
}
