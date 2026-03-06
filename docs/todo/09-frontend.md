# TODO: Frontend

Веб-интерфейс оператора: Dashboard, Chat, 3D-визуализация, администрирование. React, TypeScript, Three.js, WebSocket.

---

## Этап 1 — Инициализация проекта

- [ ] **Создать репозиторий frontend.** Vite + React + TypeScript. Зависимости: react-router-dom, zustand (state management), axios, @tanstack/react-query, tailwindcss.

- [ ] **Настроить ESLint + Prettier.** eslintrc.cjs: @typescript-eslint/recommended, react-hooks, import order. Prettierrc: singleQuote, semi, trailingComma all.

- [ ] **Настроить Tailwind CSS.** tailwind.config.ts: custom theme colors (primary, secondary, danger, warning, success), dark mode (class strategy), custom fonts.

- [ ] **Создать Dockerfile.** Multi-stage: node:20-alpine → build (vite build) → nginx:alpine (serve static). nginx.conf: SPA fallback, gzip, proxy /api → gateway, proxy /ws → gateway.

- [ ] **Vite proxy.** vite.config.ts: proxy /api → http://localhost:8005, proxy /ws → ws://localhost:8005. Для dev-режима без CORS.

- [ ] **Базовая структура.** App.tsx с React Router, Layout component (Header + Sidebar + main content), routing: /, /chat, /visualization, /admin, /login.

---

## Этап 2 — API Client и Auth

- [ ] **HTTP client (api/client.ts).** Axios instance с baseURL /api/v1, interceptor для JWT (Authorization header), interceptor для refresh token, error interceptor (redirect to /login при 401).

- [ ] **Auth API (api/auth.ts).** login(email, password) → TokenResponse, register(data) → UserDetail, getMe() → UserDetail. Сохранение token в localStorage.

- [ ] **Auth store (store/authStore.ts).** Zustand store: user, token, isAuthenticated, login(), logout(), checkAuth(). Persist middleware для localStorage.

- [ ] **Auth hook (hooks/useAuth.ts).** Хук: isAuthenticated, user, login, logout, isLoading. Protected route wrapper — redirect на /login если !isAuthenticated.

- [ ] **Login page (pages/Auth/LoginPage.tsx).** Форма: email, password, submit. Error display. Redirect на / после успешного логина.

- [ ] **React Query setup.** QueryClientProvider с default options: staleTime 30s, retry 2, refetchOnWindowFocus true. Query keys convention: ['robots'], ['tasks', taskId].

---

## Этап 3 — Dashboard

- [ ] **Dashboard page (pages/Dashboard/Dashboard.tsx).** Layout: верхняя панель метрик (cards) + список роботов (слева) + доска задач (справа). Auto-refresh через React Query polling (5s).

- [ ] **Metrics cards.** Карточки: Total Robots (по статусам: active/idle/charging/error), Active Tasks, Incidents Today, System Health (% сервисов UP). Данные из GET /api/v1/stats.

- [ ] **Robot list (pages/Dashboard/RobotList.tsx).** Таблица/список роботов: id, model, status (цветной badge), battery (progress bar), zone, last_seen (relative time). Фильтрация по status/zone. Сортировка.

- [ ] **Robot detail (components/Robot/RobotDetail.tsx).** Modal/drawer: полная информация о роботе, текущая задача, история последних задач, график батареи за 1 час (mini chart), кнопки действий (send command, stop).

- [ ] **Task board (pages/Dashboard/TaskBoard.tsx).** Kanban-доска: колонки Pending → Assigned → In Progress → Completed/Failed. Drag-and-drop для manual reassignment (SUPERVISOR+ role). Фильтрация по типу/роботу.

- [ ] **Task detail (components/Task/TaskDetail.tsx).** Modal: описание, назначенный робот, params (JSON view), result (JSON view), timeline (created → assigned → started → finished), кнопка Cancel.

- [ ] **Create task form.** Modal форма: тип задачи (select), описание (textarea), приоритет (1-5), целевая зона (select), целевой робот (optional select). POST /api/v1/tasks.

---

## Этап 4 — WebSocket и Real-time

- [ ] **WebSocket client (api/ws.ts).** WebSocket manager: connect(url, token), disconnect(), send(type, payload), onMessage(handler). Auto-reconnect с exponential backoff (1s, 2s, 4s, max 30s). Heartbeat ping/pong.

- [ ] **useWebSocket hook (hooks/useWebSocket.ts).** Хук: isConnected, lastMessage, sendMessage. Автоматическое подключение при mount, отключение при unmount. Разделение по каналам: chat, telemetry, notifications.

- [ ] **Telemetry subscription.** WS /ws/telemetry: подписка на конкретных роботов. Обновление store при получении данных. Дебаунс обновлений UI (16ms — 60fps).

- [ ] **Notifications.** WS /ws/notifications: toast-уведомления при событиях: task completed (success), task failed (error), robot offline (warning), incident (danger). Notification center с историей.

- [ ] **Robot store real-time.** Zustand robot store обновляется через WebSocket: позиции, статусы, батарея. Optimistic updates для UI.

---

## Этап 5 — Chat Interface

- [ ] **Chat page (pages/Chat/ChatPage.tsx).** Layout: history sidebar (список сессий) + main chat area + robot status sidebar. Full-height layout.

- [ ] **Message list (pages/Chat/MessageList.tsx).** Отображение сообщений: user messages (right-aligned), assistant responses (left-aligned, markdown rendering). Auto-scroll to bottom.

- [ ] **Streaming responses.** WS /ws/chat: отправка user message → получение streaming tokens → инкрементальное отображение. Typing indicator во время генерации.

- [ ] **Markdown rendering.** Рендеринг assistant responses: заголовки, списки, код, таблицы, bold/italic. Библиотека: react-markdown + remark-gfm.

- [ ] **Chat input (pages/Chat/ChatInput.tsx).** Textarea с авто-расширением, отправка по Enter (Shift+Enter для newline), кнопка отправки, disabled во время streaming.

- [ ] **Command suggestions.** Автодополнение при вводе: предложения частых команд ("переместить робот", "проверить зону", "статус всех роботов"). Dropdown под textarea.

- [ ] **Chat sessions.** Sidebar: список прошлых чат-сессий, создание нового чата, удаление. Загрузка истории из API.

---

## Этап 6 — 3D-визуализация

- [ ] **Three.js setup (pages/Visualization/Scene3D.tsx).** React Three Fiber (R3F) canvas: scene, camera (OrbitControls), lighting (ambient + directional), grid helper. Full-screen mode.

- [ ] **Environment map (pages/Visualization/EnvironmentMap.tsx).** Отображение карты зон: плоскости с границами зон (из API), цветовая кодировка по типу (warehouse=blue, inspection=yellow). Labels с названиями.

- [ ] **Robot models (pages/Visualization/RobotModel.tsx).** 3D-модели роботов (.glb) размещённые на карте. Позиция обновляется в real-time через WebSocket. Цвет по статусу (green=active, gray=idle, red=error).

- [ ] **Robot trajectories.** Линии траекторий: текущий путь (пунктир), пройденный путь (сплошная, fade out). Включение/выключение per-robot.

- [ ] **Camera controls (pages/Visualization/CameraControls.tsx).** OrbitControls: вращение, zoom, pan. Кнопки: top view, follow robot (camera привязана к выбранному роботу), reset view.

- [ ] **Object markers.** Отображение обнаруженных объектов на карте: иконки/markers с class name и confidence. Обновление из Feature Store через WebSocket.

- [ ] **Selection and info.** Клик на робота/объект → popup с информацией. Highlight выбранного робота. Integration с Dashboard (клик → открыть Robot Detail).

---

## Этап 7 — Admin Panel

- [ ] **Admin page (pages/Admin/AdminPage.tsx).** Tabs: Users, System Config, Zones, Models. Доступ только для ADMIN role.

- [ ] **User management (pages/Admin/UserManagement.tsx).** Таблица пользователей: CRUD. Форма: name, email, role (select), is_active (toggle). Смена пароля. Деактивация.

- [ ] **System config (pages/Admin/SystemConfig.tsx).** Key-value editor для конфигураций: MQTT settings, alert thresholds, feature flags. Загрузка из GET /api/v1/configurations, обновление через PUT.

- [ ] **Zone editor.** CRUD зон: name, type, boundaries (JSON editor или visual polygon editor на 2D карте), max_robots.

- [ ] **Model management.** Список моделей из MinIO: name, version, status, deployed_at, metrics. Кнопки: deploy, rollback, delete. Статус развёртывания.

---

## Этап 8 — UI/UX Polish

- [ ] **Dark/Light theme.** Toggle в header. Tailwind dark mode (class strategy). Сохранение в localStorage.

- [ ] **Responsive layout.** Адаптация для tablet (sidebar collapse) и mobile (bottom navigation). Breakpoints: sm, md, lg, xl.

- [ ] **Loading states.** Skeleton loaders для всех lists/cards. Spinner для actions (create, delete). Optimistic updates где возможно.

- [ ] **Error handling.** Error boundaries для каждого major section. Fallback UI: "Something went wrong" + retry button. Toast для API errors.

- [ ] **Accessibility.** ARIA labels, keyboard navigation, focus management для modals, color contrast compliance (WCAG AA).

- [ ] **Internationalization (i18n).** Подготовка: все строки вынесены в constants/locale файлы. Базовые языки: русский (primary), английский. Библиотека: react-i18next.

---

## Этап 9 — Тесты

- [ ] **Test setup.** Vitest + @testing-library/react + msw (Mock Service Worker) для API mocking.

- [ ] **Component tests.** Тесты: RobotCard (render with different statuses), TaskCard (render, click handlers), MessageList (scroll behavior), Button/Modal/Table (common components).

- [ ] **Page tests.** Тесты: Dashboard (loads robots, loads tasks), ChatPage (send message, receive streaming response), LoginPage (form validation, submit).

- [ ] **Hook tests.** Тесты: useAuth (login flow, logout, token refresh), useWebSocket (connect, reconnect, message handling), useRobots (fetch, real-time updates).

- [ ] **E2E tests (Playwright).** Сценарии: login → dashboard → view robot → open chat → send command → see task created → see task in kanban. Headless mode в CI.
