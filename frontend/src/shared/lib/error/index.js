import { mapApiError } from '../../api/dtoMappers';

export const normalizeDomainError = (error) => mapApiError(error);
export const getErrorMessage = (error) => normalizeDomainError(error).message;
