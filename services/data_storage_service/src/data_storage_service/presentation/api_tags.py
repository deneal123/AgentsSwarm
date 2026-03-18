"""Метаданные тегов OpenAPI для документации API."""

# Теги для группировки роутов в Swagger UI
API_TAGS = [
    {
        "name": "Authentication",
        "description": "Аутентификация и авторизация. Вход, выход, регистрация, "
        "обновление токенов, гостевые сессии.",
    },
    {
        "name": "Profile",
        "description": "Управление профилем пользователя. Просмотр и обновление данных аккаунта.",
    },
    {
        "name": "Files",
        "description": "Загрузка и хранение файлов: конфиги правил (YAML/TOML) и датасеты (Excel).",
    },
    {
        "name": "Rules",
        "description": "Маркетплейс правил. Просмотр, создание версий, управление каталогом (admin), "
        "настройка персональных предпочтений и снепшот активных правил пользователя.",
    },
    {
        "name": "Playground",
        "description": "Анализ коммуникаций в режиме playground. Одиночный и пакетный анализ, "
        "управление задачами, просмотр результатов.",
    },
    {
        "name": "Pipeline",
        "description": "Запуск пакетного анализа датасетов через pipeline. "
        "Управление задачами, просмотр отчётов, скачивание артефактов.",
    },
    {
        "name": "Communication Results",
        "description": "Результаты анализа коммуникаций по задачам. "
        "Поиск, фильтрация, статистика по рискам.",
    },
    {
        "name": "Tasks-WebSocket",
        "description": "WebSocket-подключение для получения статуса задач в реальном времени.",
    },
]

# Справочник имён тегов для удобного обращения из кода
TAG_NAMES = {
    "auth": "Authentication",
    "profile": "Profile",
    "files": "Files",
    "rules": "Rules",
    "playground": "Playground",
    "pipeline": "Pipeline",
    "communication_results": "Communication Results",
    "tasks_ws": "Tasks-WebSocket",
}
