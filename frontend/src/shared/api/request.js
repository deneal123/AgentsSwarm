import httpClient from './httpClient';

export const createApiMethod = (configBuilder, mapper = null) => async (payload = {}, options = {}) => {
  const response = await httpClient.request(configBuilder(payload, options));
  const body = response?.data;
  return typeof mapper === 'function' ? mapper(body) : body;
};

export const request = async (config, mapper = null) => {
  const response = await httpClient.request(config);
  const payload = response?.data;
  return typeof mapper === 'function' ? mapper(payload) : payload;
};
