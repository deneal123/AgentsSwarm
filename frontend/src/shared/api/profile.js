import { request } from './request';
import { mapProfileDto } from './dtoMappers';

export const fetchProfile = ({ signal } = {}) =>
  request({ method: 'get', url: '/api/profile/me', signal }, mapProfileDto);

export const updateProfile = (payload, { signal } = {}) =>
  request({ method: 'patch', url: '/api/profile/me', data: payload, signal }, mapProfileDto);

export const deleteChatHistory = ({ signal } = {}) =>
  request({ method: 'delete', url: '/api/profile/me/chat-history', signal });

/** Billing quota endpoint not available — resolves to null */
export const getUserQuota = () => Promise.resolve(null);
