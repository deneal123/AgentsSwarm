const DEFAULT_FALLBACK_MESSAGE = 'Не удалось выполнить действие. Попробуйте ещё раз.';
const NETWORK_MESSAGE = 'Нет соединения с сервером. Проверьте интернет или повторите позже.';

const STATUS_MESSAGES = {
  400: 'Некорректные данные. Проверьте введённую информацию и попробуйте снова.',
  401: 'Сессия истекла или доступ запрещён. Авторизуйтесь снова.',
  403: 'Доступ ограничен или исчерпан лимит. Обратитесь к администратору или повторите позже.',
  404: 'Запрашиваемые данные не найдены.',
  409: 'Конфликт данных. Обновите страницу и повторите попытку.',
  413: 'Файл слишком большой. Уменьшите размер и загрузите его снова.',
  415: 'Неподдерживаемый формат файла.',
  429: 'Слишком много запросов. Подождите немного и повторите.',
  500: 'На сервере произошла ошибка. Попробуйте позже.',
  502: 'Сервис недоступен. Повторите попытку чуть позже.',
  503: 'Сервис временно недоступен. Попробуйте позже.',
};

const CODE_MESSAGES = {
  DATASET_REMOVED: 'Файл уже удалён. Обновите список датасетов, чтобы увидеть актуальное состояние.',
  JOB_LIMIT_REACHED: 'Лимит запусков исчерпан. Подождите перед новой попыткой или обратитесь к администратору.',
  FILE_TOO_LARGE: STATUS_MESSAGES[413],
  REQUEST_CANCELED: 'Запрос отменён.',
};

const isLikelyErrorCode = (value) => typeof value === 'string' && /^[A-Z0-9_]+$/.test(value.trim());

const normalizeDetail = (detail) => {
  if (!detail && detail !== 0) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => normalizeDetail(item?.msg || item?.message || item?.detail || item)).filter(Boolean).join('; ');
  if (typeof detail === 'object') {
    if (detail.message) return normalizeDetail(detail.message);
    if (detail.detail) return normalizeDetail(detail.detail);
    if (detail.msg) return normalizeDetail(detail.msg);
    const nested = Object.values(detail).map((value) => normalizeDetail(value)).filter(Boolean).join('; ');
    if (nested) return nested;
    return JSON.stringify(detail);
  }
  return String(detail);
};

export const mapIdentity = (data) => data;

export const mapApiError = (error, options = {}) => {
  const status = error?.response?.status ?? error?.status ?? null;
  const data = error?.response?.data ?? error?.details ?? null;
  const rawDetail = data?.detail ?? data?.message ?? data?.error ?? data ?? error?.message;
  let code = options.kind === 'canceled' ? 'REQUEST_CANCELED' : (data?.code ?? error?.code ?? null);
  if (!code && rawDetail && typeof rawDetail === 'object' && rawDetail.code) code = rawDetail.code;
  if (!code && typeof rawDetail === 'string' && isLikelyErrorCode(rawDetail)) code = rawDetail.trim();

  const details = normalizeDetail(rawDetail) || null;
  const message = CODE_MESSAGES[code] || STATUS_MESSAGES[status] || (!status ? NETWORK_MESSAGE : DEFAULT_FALLBACK_MESSAGE);

  return {
    type: 'DomainError',
    code: code || 'UNKNOWN_ERROR',
    message,
    details,
    status,
    isRetryable: !status || status >= 500 || status === 429,
    isCanceled: code === 'REQUEST_CANCELED',
    raw: error,
  };
};

export const mapChatUploadResponse = (data = {}) => {
  const extractedText = data.extracted_text || '';
  return {
    ...data,
    file_id: data.file_id || `file_${Date.now()}_${Math.random()}`,
    download_url: data.download_url || data.file_url || null,
    file_context: extractedText,
    content_preview: extractedText,
  };
};

export const mapModelsResponse = (data = {}) => data?.models || [];
export const mapProfileDto = (data = {}) => ({ ...data });
export const mapJobDto = (data = {}) => ({ ...data });
export const mapPlatformStatsDto = (data = {}) => ({ ...data });
export const mapFileDownloadDto = (data = {}) => ({ ...data });
