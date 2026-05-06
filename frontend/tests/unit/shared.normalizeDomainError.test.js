import { normalizeDomainError } from '../../src/shared/lib/error';

describe('normalizeDomainError', () => {
  it('normalizes network error', () => {
    const error = { message: 'Network Error', code: 'ERR_NETWORK' };

    expect(normalizeDomainError(error)).toMatchObject({
      status: null,
      code: 'ERR_NETWORK',
      message: 'Нет соединения с сервером. Проверьте интернет или повторите позже.',
      details: 'Network Error',
    });
  });

  it('normalizes unauthorized and forbidden errors', () => {
    const unauthorized = { response: { status: 401, data: { detail: 'token expired' } } };
    const forbidden = { response: { status: 403, data: { detail: 'forbidden' } } };

    expect(normalizeDomainError(unauthorized)).toMatchObject({
      status: 401,
      message: 'Сессия истекла или доступ запрещён. Авторизуйтесь снова.',
      details: 'token expired',
    });

    expect(normalizeDomainError(forbidden)).toMatchObject({
      status: 403,
      message: 'Доступ ограничен или исчерпан лимит. Обратитесь к администратору или повторите позже.',
      details: 'forbidden',
    });
  });

  it('normalizes 5xx errors', () => {
    const serverError = { response: { status: 500, data: { detail: 'internal' } } };

    expect(normalizeDomainError(serverError)).toMatchObject({
      status: 500,
      message: 'На сервере произошла ошибка. Попробуйте позже.',
      details: 'internal',
    });
  });

  it('handles unknown error with fallback message', () => {
    const unknown = { response: { status: 418, data: { detail: { foo: 'bar' } } } };

    expect(normalizeDomainError(unknown, { fallbackMessage: 'Что-то пошло не так' })).toMatchObject({
      status: 418,
      message: 'Что-то пошло не так',
      details: 'bar',
    });
  });
});
