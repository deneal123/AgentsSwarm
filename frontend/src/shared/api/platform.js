import { request } from './request';

export const getPlatformStats = ({ signal } = {}) => request({ method: 'get', url: '/api/ml/v1/platform/stats', signal });
