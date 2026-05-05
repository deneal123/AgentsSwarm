# Тестирование AI Chat Frontend

Этот документ описывает стратегию тестирования и запуск тестов для проекта GPTHub (AI-агенты для здоровья и питания).

## 📋 Структура тестирования

```
tests/
├── unit/                 # Unit тесты компонентов и hooks
│   ├── components/       # Тесты React компонентов
│   └── hooks/           # Тесты custom hooks
├── integration/         # Integration тесты
│   └── analytics.test.js # Тесты аналитики
└── e2e/                 # End-to-end тесты
    ├── playwright.config.js
    ├── smoke.spec.js     # Базовые smoke тесты
    ├── chat.spec.js      # Тесты чат-функциональности
    └── auth-limits.spec.js # Тесты аутентификации и лимитов
```

## 🧪 Типы тестов

### Unit тесты (`tests/unit/`)
- Тестируют отдельные компоненты и hooks
- Используют Jest + React Testing Library
- Фокус на логике и взаимодействии

### Integration тесты (`tests/integration/`)
- Тестируют взаимодействие между компонентами
- Проверяют API интеграцию
- Тестируют пользовательские сценарии

### E2E тесты (`tests/e2e/`)
- Полноценное тестирование пользовательских сценариев
- Используют Playwright для браузерного тестирования
- Проверяют critical user journeys

## 🚀 Запуск тестов

### Unit тесты
```bash
# Запуск всех unit тестов
npm run test:unit

# Запуск с watch mode
npm run test:watch

# Запуск с coverage
npm run test:coverage
```

### Integration тесты
```bash
npm run test:integration
```

### E2E тесты
```bash
# Установка Playwright браузеров
npm run e2e:install

# Запуск на Chromium
npm run e2e:run

# Запуск на всех браузерах
npm run e2e:all

# Только desktop браузеры
npm run e2e:desktop

# Только мобильные браузеры
npm run e2e:mobile
```

### Все тесты
```bash
npm run test:all
```

## 📊 Покрытие тестами

### Компоненты с тестами:
- ✅ `SearchInterface` — главный поисковый интерфейс
- ✅ `VoiceRecorder` — запись голосовых сообщений
- ✅ `MessageReactions` — система реакций
- ✅ `useGuestSession` — управление гостевыми сессиями

### Функциональность с тестами:
- ✅ **Чат-функциональность** — отправка сообщений, получение ответов
- ✅ **Аутентификация** — лимиты, модальные окна, навигация
- ✅ **Аналитика** — трекинг событий, batching, privacy
- ✅ **Responsive дизайн** — мобильная адаптация
- ✅ **Keyboard shortcuts** — горячие клавиши

### E2E сценарии:
- ✅ **Smoke тесты** — базовая загрузка и элементы интерфейса
- ✅ **Chat flow** — полный цикл общения с AI
- ✅ **Auth limits** — обработка лимитов и регистрация
- ✅ **Voice messages** — голосовой ввод
- ✅ **Mobile experience** — работа на мобильных устройствах

## 🎯 Критерии качества

### Coverage цели:
- **Statements**: > 70%
- **Branches**: > 70%
- **Functions**: > 70%
- **Lines**: > 70%

### E2E покрытие:
- **Critical user journeys**: 100%
- **Error scenarios**: 90%
- **Edge cases**: 80%

## 🔧 Настройка тестового окружения

### Переменные окружения для E2E:
```bash
# URL тестового сервера
E2E_BASE_URL=http://localhost:3000

# API endpoints для mocking
API_BASE_URL=http://localhost:8000/api
```

### Mock данные:
- API responses для чата
- WebSocket события
- User session data
- Analytics payloads

## 🐛 Debugging тестов

### Unit тесты:
```bash
# С подробным выводом
npm run test:unit -- --verbose

# Только failed тесты
npm run test:unit -- --onlyFailures

# С конкретным тестом
npm run test:unit -- SearchInterface
```

### E2E тесты:
```bash
# С видео и скриншотами
DEBUG=pw:api npm run e2e:run

# Headed mode (видимый браузер)
npx playwright test --headed

# Отладка конкретного теста
npx playwright test --debug chat.spec.js
```

## 📈 CI/CD интеграция

### GitHub Actions workflow:
```yaml
- name: Run tests
  run: |
    npm run test:unit
    npm run test:integration
    npm run e2e:run
- name: Upload coverage
  uses: codecov/codecov-action@v3
- name: Upload E2E artifacts
  uses: actions/upload-artifact@v3
  with:
    name: e2e-results
    path: tmp_e2e/
```

## 🔍 Мониторинг качества

### Метрики для отслеживания:
- **Test execution time** — время выполнения тестов
- **Flaky tests** — нестабильные тесты
- **Coverage trends** — тренды покрытия
- **E2E success rate** — процент успешных E2E прогонов

### Регулярные проверки:
- **Daily**: Unit и integration тесты
- **Weekly**: Полный E2E suite
- **Monthly**: Performance regression tests

## 🚨 Обработка ошибок

### Common issues:
- **Flaky E2E tests** — добавить retries и waits
- **Network timeouts** — увеличить timeouts для API calls
- **Race conditions** — использовать proper async/await patterns
- **Browser compatibility** — тестировать на всех target browsers

### Best practices:
- **Isolation** — каждый тест независимый
- **Cleanup** — очищать состояние после тестов
- **Mocking** — мокировать внешние зависимости
- **Realistic data** — использовать правдоподобные тестовые данные

## 📚 Ресурсы

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Testing Library Principles](https://testing-library.com/docs/guiding-principles/)

---

**Тестирование гарантирует качество и надежность AI-чат платформы для здоровья и питания!** 🏥🤖
