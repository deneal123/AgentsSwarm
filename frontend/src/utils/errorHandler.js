import { getErrorMessage, normalizeDomainError } from '../shared/lib/error';

export function extractErrorInfo(error, options = {}) {
  const { fallbackMessage } = options;
  const normalized = normalizeDomainError(error, { fallbackMessage });
  return {
    status: normalized.status,
    code: normalized.code,
    technicalMessage: normalized.details,
    userMessage: normalized.message,
    isNetworkError: !normalized.status,
    raw: normalized.raw,
  };
}

export function getUserFacingMessage(error, options = {}) {
  return getErrorMessage(error, options);
}

export function showErrorToast(toast, error, options = {}) {
  const info = extractErrorInfo(error, options);
  if (typeof toast === 'function') {
    toast({
      title: options.title || 'Ошибка',
      description: info.userMessage,
      status: options.status || 'error',
      duration: options.duration ?? 6000,
      isClosable: true,
    });
  }
  return info;
}

export default extractErrorInfo;
