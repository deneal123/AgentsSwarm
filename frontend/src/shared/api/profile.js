import { request } from './request';
import { mapProfileDto } from './dtoMappers';

export const fetchProfile = ({ signal } = {}) => request({ method: 'get', url: '/api/profile/me', signal }, mapProfileDto);
export const updateProfile = (payload, { signal } = {}) => request({ method: 'patch', url: '/api/profile/me', data: payload, signal }, mapProfileDto);
export const getQuotaPlans = ({ signal } = {}) => request({ method: 'get', url: '/api/billing/quotas/preview', signal }, mapProfileDto);
export const getUserQuota = ({ signal } = {}) => request({ method: 'get', url: '/api/billing/quota', signal }, mapProfileDto);
