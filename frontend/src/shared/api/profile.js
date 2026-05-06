import { request } from './request';

export const fetchProfile = ({ signal } = {}) => request({ method: 'get', url: '/api/profile/me', signal });
export const updateProfile = (payload, { signal } = {}) => request({ method: 'patch', url: '/api/profile/me', data: payload, signal });
export const getQuotaPlans = ({ signal } = {}) => request({ method: 'get', url: '/api/billing/quotas/preview', signal });
export const getUserQuota = ({ signal } = {}) => request({ method: 'get', url: '/api/billing/quota', signal });
