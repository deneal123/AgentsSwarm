# TODO: SmolVLA Service

Микросервис Vision-Language-Action моделей. Cloud-версия SmolVLA и X-VLA для генерации действий роботов. gRPC API, fine-tuning, action chunking.

---

## Этап 1 — Инициализация проекта

- [ ] **Создать репозиторий smolvla_service.** Poetry-проект с зависимостями: lerobot, torch, transformers, grpcio, grpcio-tools, fastapi, uvicorn, pydantic-settings, prometheus-client, structlog.

- [ ] **Настроить .pre-commit-config.yaml.** Хуки: ruff, mypy, bandit.

- [ ] **Создать Dockerfile.** Базовый образ `nvidia/cuda:12.1-devel-ubuntu22.04`, установка PyTorch + LeRobot. HEALTHCHECK через gRPC health check.

- [ ] **Создать config.py.** Pydantic Settings: SMOLVLA_MODEL_ID (lerobot/smolvla_base), XVLA_MODEL_ID (lerobot/xvla-base), DEVICE (cuda:0), DTYPE (bfloat16/float16), ACTIONS_PER_CHUNK (50), MAX_CAMERAS (3), GRPC_PORT (50051), LOG_LEVEL, JAEGER_ENDPOINT.

- [ ] **Создать main.py.** Entrypoint: загрузка моделей → запуск gRPC server + FastAPI health endpoint.

---

## Этап 2 — gRPC сервер

- [ ] **Proto-определение (smolvla.proto).** Сервис SmolVLAService: PredictAction (image + instruction + joint_state → action_chunk), GetModelInfo, HealthCheck. Messages: ImageInput, JointState, ActionChunk, ActionPoint.

- [ ] **gRPC Servicer (server/grpc_server.py).** Реализация SmolVLAServicer: приём запроса, вызов inference, возврат action chunk. Async с thread pool для GPU inference.

- [ ] **Health check.** gRPC Health Checking Protocol: модель загружена, GPU available, warmup completed.

- [ ] **Streaming inference.** Bidirectional streaming RPC: клиент стримит кадры + joint_state, сервер стримит action chunks. Для непрерывного управления роботом.

---

## Этап 3 — SmolVLA Inference

- [ ] **Model loader (inference/smolvla.py).** Загрузка SmolVLA из HuggingFace Hub или MinIO. Параметры: device, dtype, torch.compile (опционально для ускорения).

- [ ] **Image preprocessing.** Конвертация входных изображений: resize до модельного разрешения, нормализация, multi-camera concatenation (до 3 ракурсов).

- [ ] **Instruction encoding.** Токенизация текстовой инструкции через встроенный tokenizer. Max length: 128 tokens для edge-совместимости.

- [ ] **Joint state input.** Приём текущего состояния суставов робота (proprioception) как дополнительный вход модели. Нормализация по ranges конкретного робота.

- [ ] **Action chunk generation (inference/action_chunking.py).** Flow Matching декодирование: генерация chunk из N действий (configurable, default 50). Каждое действие: 7D вектор (dx, dy, dz, droll, dpitch, dyaw, gripper).

- [ ] **Action smoothing.** Сглаживание между последовательными chunks: overlap region, exponential blending для плавных переходов.

---

## Этап 4 — X-VLA Inference

- [ ] **Model loader (inference/xvla.py).** Загрузка X-VLA (lerobot/xvla-base, 0.9B params). Требования: ~4 GB GPU memory в BF16.

- [ ] **Soft Prompts.** Загрузка domain-specific Soft Prompts по Domain ID робота. Реестр: domain_id → soft_prompt_path (MinIO). До 30 различных конфигураций роботов.

- [ ] **Domain ID management.** API для управления Domain ID: регистрация нового робота, привязка soft prompt, обновление. Хранение маппинга в Redis.

- [ ] **Cross-robot inference.** Один X-VLA instance обслуживает роботов разных типов: подмена soft prompts на лету при каждом запросе (без перезагрузки модели).

---

## Этап 5 — Fine-tuning pipeline

- [ ] **Dataset loader (training/dataset.py).** Загрузка LeRobot-совместимых датасетов из MinIO. Формат: episodes с image observations + actions + language instructions. Конвертация в LeRobotDataset.

- [ ] **Fine-tuner (training/fine_tuner.py).** Fine-tuning SmolVLA на кастомных данных: конфигурация lr, batch_size, epochs, gradient_accumulation. Сохранение чекпоинтов в MinIO.

- [ ] **Soft Prompt training (X-VLA).** Обучение только Soft Prompts для нового типа робота: заморозка backbone, обучение ~9M параметров (1% от модели). ~300× экономия compute vs полное дообучение.

- [ ] **Evaluator (training/evaluator.py).** Оценка quality: success rate на validation episodes, trajectory smoothness, action prediction error. Автоматическое сравнение с baseline.

- [ ] **Model versioning.** Сохранение каждой обученной версии в MinIO с метаданными (training config, metrics, dataset version). Регистрация в PostgreSQL (model_versions table).

---

## Этап 6 — Asynchronous Inference (PolicyServer)

- [ ] **PolicyServer паттерн.** Реализация LeRobot PolicyServer: следующий action chunk вычисляется параллельно с выполнением текущего на роботе. Устранение inference latency из цикла управления.

- [ ] **Action queue.** Внутренняя очередь предвычисленных action chunks. При запросе от робота — мгновенная выдача из очереди + запуск inference для следующего chunk.

- [ ] **Prefetch strategy.** Предвычисление следующего chunk за 1-2 шага до окончания текущего. Адаптивный trigger: при оставшихся < 10 действиях в текущем chunk.

---

## Этап 7 — Тесты

- [ ] **conftest.py.** Фикстуры: mock SmolVLA model (random action output), sample images (224×224), sample joint states, sample instructions.

- [ ] **Unit: action chunking.** Тесты генерации chunks: correct dimensions (N×7), smoothing между chunks, edge cases (chunk_size=1).

- [ ] **Unit: preprocessing.** Тесты image resize, multi-camera concat, joint state normalization, instruction tokenization.

- [ ] **Unit: Soft Prompts.** Тесты загрузки/подмены soft prompts, domain ID validation, unknown domain fallback.

- [ ] **Integration: gRPC.** Тесты PredictAction RPC: unary + streaming, правильные protobuf типы, timeout handling.

- [ ] **Integration: fine-tuning.** Тест pipeline: загрузка mini-dataset → 1 epoch training → checkpoint save → evaluation. Требует GPU.
