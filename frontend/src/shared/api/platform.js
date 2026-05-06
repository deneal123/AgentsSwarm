import { request } from './request';
import { mapPlatformStatsDto } from './dtoMappers';

export const getPlatformStats = ({ signal } = {}) => request({ method: 'get', url: '/api/ml/v1/platform/stats', signal }, mapPlatformStatsDto);
