const DEFAULT_FALLBACK_MESSAGE = "Не удалось выполнить действие. Попробуйте ещё раз.";
const NETWORK_MESSAGE = "Нет соединения с сервером. Проверьте интернет или повторите позже.";

const STATUS_MESSAGES = {
  400: "Некорректные данные. Проверьте введённую информацию и попробуйте снова.",
  401: "Сессия истекла или доступ запрещён. Авторизуйтесь снова.",
  403: "Доступ ограничен или исчерпан лимит. Обратитесь к администратору или повторите позже.",
  404: "Запрашиваемые данные не найдены.",
  409: "Конфликт данных. Обновите страницу и повторите попытку.",
  413: "Файл слишком большой. Уменьшите размер и загрузите его снова.",
  415: "Неподдерживаемый формат файла.",
  429: "Слишком много запросов. Подождите немного и повторите.",
  500: "На сервере произошла ошибка. Попробуйте позже.",
  502: "Сервис недоступен. Повторите попытку чуть позже.",
  503: "Сервис временно недоступен. Попробуйте позже.",
};

const CODE_MESSAGES = {
  DATASET_REMOVED:
    "Файл уже удалён. Обновите список датасетов, чтобы увидеть актуальное состояние.",
  JOB_LIMIT_REACHED:
    "Лимит запусков исчерпан. Подождите перед новой попыткой или обратитесь к администратору.",
  FILE_TOO_LARGE: STATUS_MESSAGES[413],
};

const DETAIL_PATTERNS = [
  {
    test: /no available launches/i,
    message: "Лимит запусков исчерпан. Подождите и попробуйте снова.",
  },
  { test: /invalid credentials/i, message: "Неверный логин или пароль." },
  { test: /user already exists/i, message: "Пользователь с таким email уже зарегистрирован." },
  { test: /dataset already exists/i, message: "Такой датасет уже существует." },
  { test: /file too large|request entity too large/i, message: STATUS_MESSAGES[413] },
];

const normalizeDetail = (detail) => {
  if (!detail && detail !== 0) return "";
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => normalizeDetail(item?.msg || item?.message || item?.detail || item))
      .filter(Boolean)
      .join("; ");
  }

  if (typeof detail === "object") {
    if (detail.message) return normalizeDetail(detail.message);
    if (detail.detail) return normalizeDetail(detail.detail);
    if (detail.msg) return normalizeDetail(detail.msg);
    const nested = Object.values(detail)
      .map((value) => normalizeDetail(value))
      .filter(Boolean)
      .join("; ");
    if (nested) return nested;
    try {
      return JSON.stringify(detail);
    } catch (error) {
      return String(detail);
    }
  }

  return String(detail);
};

const isLikelyErrorCode = (value) => typeof value === "string" && /^[A-Z0-9_]+$/.test(value.trim());

export function extractErrorInfo(error, options = {}) {
  const { fallbackMessage = DEFAULT_FALLBACK_MESSAGE } = options;
  const status = error?.response?.status;
  const data = error?.response?.data;
  const rawDetail = data?.detail ?? data?.message ?? data?.error ?? data;

  let code = data?.code;
  if (!code && rawDetail && typeof rawDetail === "object" && rawDetail.code) {
    code = rawDetail.code;
  }
  if (!code && typeof rawDetail === "string" && isLikelyErrorCode(rawDetail)) {
    code = rawDetail.trim();
  }

  let technicalMessage = normalizeDetail(rawDetail);
  if (!technicalMessage && typeof error?.message === "string") {
    technicalMessage = error.message;
  }

  let userMessage = fallbackMessage;
  if (!error?.response) {
    userMessage = NETWORK_MESSAGE;
  }
  if (status && STATUS_MESSAGES[status]) {
    userMessage = STATUS_MESSAGES[status];
  }
  if (code && CODE_MESSAGES[code]) {
    userMessage = CODE_MESSAGES[code];
  }
  if (technicalMessage) {
    const pattern = DETAIL_PATTERNS.find((entry) => entry.test.test(technicalMessage));
    if (pattern) {
      userMessage = pattern.message;
    }
  }

  return {
    status: status ?? null,
    code: code ?? null,
    technicalMessage: technicalMessage || null,
    userMessage: userMessage || fallbackMessage,
    isNetworkError: !error?.response,
    raw: error,
  };
}

export function getUserFacingMessage(error, options = {}) {
  return extractErrorInfo(error, options).userMessage;
}

export function showErrorToast(toast, error, options = {}) {
  const info = extractErrorInfo(error, options);
  if (typeof toast === "function") {
    toast({
      title: options.title || "Ошибка",
      description: info.userMessage,
      status: options.status || "error",
      duration: options.duration ?? 6000,
      isClosable: true,
    });
  }
  return info;
}

export default extractErrorInfo;
