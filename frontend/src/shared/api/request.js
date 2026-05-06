import httpClient from './httpClient';

export const request = async (config, mapper = null) => {
  const response = await httpClient.request(config);
  const payload = response?.data;
  return typeof mapper === 'function' ? mapper(payload) : payload;
};
