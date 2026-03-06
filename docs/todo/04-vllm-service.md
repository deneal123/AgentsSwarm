# TODO: vLLM Service

Микросервис для inference языковых и мультимодальных моделей. OpenAI-совместимый API, LoRA-адаптеры, streaming.

---

## Этап 1 — Инициализация проекта

- [ ] **Создать репозиторий vllm_service.** Poetry-проект с зависимостями: vllm, fastapi, uvicorn, pydantic-settings, prometheus-client, opentelemetry-api, structlog.

- [ ] **Настроить .pre-commit-config.yaml.** Хуки: ruff, mypy, bandit.

- [ ] **Создать Dockerfile.** Базовый образ `vllm/vllm-openai:latest` или `nvidia/cuda:12.1-devel-ubuntu22.04` с установкой vllm. NVIDIA runtime, HEALTHCHECK /health.

- [ ] **Создать config.py.** Pydantic Settings: MODEL_NAME (Qwen2.5-7B-Instruct), MULTIMODAL_MODEL (SmolVLM2-2.2B-Instruct), GPU_MEMORY_UTILIZATION (0.9), MAX_MODEL_LEN, TENSOR_PARALLEL_SIZE, LORA_MODULES_PATH, QUANTIZATION (awq/gptq/none), LOG_LEVEL, JAEGER_ENDPOINT.

- [ ] **Создать main.py.** Entrypoint: запуск vLLM AsyncLLMEngine + FastAPI wrapper для кастомных эндпоинтов и health probes.

---

## Этап 2 — Запуск vLLM Engine

- [ ] **Launcher (server/launcher.py).** Инициализация AsyncLLMEngine с параметрами из config: model, quantization, gpu_memory_utilization, max_model_len, tensor_parallel_size. Graceful shutdown.

- [ ] **Текстовая модель — Qwen2.5-7B-Instruct.** Конфигурация запуска: trust_remote_code, dtype=auto, max_model_len=8192. Проверка загрузки модели из MinIO или HuggingFace Hub.

- [ ] **Мультимодальная модель — SmolVLM2-2.2B-Instruct.** Конфигурация: limit_mm_per_prompt (images=1, video_frames=8), dtype=bfloat16. Проверка обработки изображений и видео.

- [ ] **Health probes (server/health.py).** GET /health — liveness (процесс жив). GET /ready — readiness (модель загружена, GPU available, KV-cache инициализирован).

---

## Этап 3 — OpenAI-совместимый API

- [ ] **Chat Completions (api/chat.py).** POST /v1/chat/completions — полная совместимость с OpenAI формат: messages (system/user/assistant), temperature, max_tokens, top_p, stream. Streaming через SSE.

- [ ] **Completions (api/completions.py).** POST /v1/completions — legacy endpoint для plain text completion. Поддержка prompt, max_tokens, stop sequences.

- [ ] **Models list (api/models.py).** GET /v1/models — список загруженных моделей (основная + multimodal + LoRA-адаптеры). Формат совместим с OpenAI.

- [ ] **Tool Calling.** Поддержка function calling в chat completions: tools definition, tool_choice (auto/required/none), парсинг tool_calls из ответа модели. Используется Orchestrator для structured output.

- [ ] **Structured Output.** Поддержка response_format: json_object и json_schema. Guided decoding для гарантированно валидного JSON в ответах планирования.

---

## Этап 4 — Мультимодальный анализ

- [ ] **Image input.** Приём изображений в chat messages: base64-encoded в content array (type: image_url) или URL на MinIO presigned link. Конвертация в формат SmolVLM2.

- [ ] **Video input.** Приём коротких видео (до 8 кадров): base64 или URL. Извлечение кадров, подача в SmolVLM2 как multi-image input.

- [ ] **Scene analysis endpoint.** POST /v1/analyze/scene — специализированный эндпоинт: принимает image + text query, возвращает structured JSON с описанием сцены, обнаруженными объектами, рекомендациями.

- [ ] **Маршрутизация моделей.** Автоматический выбор модели по содержимому запроса: если есть images/video → SmolVLM2, если только text → Qwen2.5. Configurable через header X-Model.

---

## Этап 5 — LoRA-адаптеры

- [ ] **LoRA Registry (lora/registry.py).** Реестр доступных LoRA-адаптеров: name, path (MinIO или local), base_model, domain. Загрузка реестра из конфигурационного файла или Redis.

- [ ] **LoRA Manager (lora/manager.py).** Динамическая загрузка/выгрузка LoRA-адаптеров без перезапуска сервера. Максимум 4 одновременных адаптера (vLLM limitation). LRU-стратегия при превышении лимита.

- [ ] **LoRA API endpoints.** GET /v1/lora — список загруженных адаптеров. POST /v1/lora/load — загрузка адаптера по имени. DELETE /v1/lora/{name} — выгрузка. Выбор адаптера через параметр model в запросе.

- [ ] **Квантизация + LoRA.** Проверка совместимости: AWQ base model + LoRA adapter (QLoRA pattern). Конфигурация quantization_config в config.py.

- [ ] **LoRA для доменной адаптации.** Адаптеры: warehouse_planner (складская логистика), inspection_reporter (инспекция), manipulation_planner (манипуляция). Каждый fine-tuned на доменных данных.

---

## Этап 6 — Оптимизация производительности

- [ ] **PagedAttention настройка.** Конфигурация block_size, swap_space, gpu_memory_utilization. Мониторинг KV-cache utilization через метрики.

- [ ] **Continuous Batching.** Настройка max_num_batched_tokens, max_num_seqs для оптимального throughput. Benchmark: target 50+ tokens/sec при batch=8.

- [ ] **Quantization.** Сравнение AWQ vs GPTQ для Qwen2.5-7B: качество (perplexity), скорость (tokens/sec), memory (GB). Выбор оптимального метода.

- [ ] **Tensor Parallelism.** Для multi-GPU setup: TENSOR_PARALLEL_SIZE=2/4. Тест распределения модели на 2× A10G vs 1× A100.

- [ ] **Prefix caching.** Включение automatic prefix caching для повторяющихся system prompts (одинаковые instructions для всех запросов планирования).

---

## Этап 7 — Тесты

- [ ] **conftest.py.** Фикстуры: mock vLLM engine (без реального GPU), sample chat messages, sample images (base64), test LoRA configs.

- [ ] **Unit: config.** Валидация конфигурации: обязательные поля, допустимые значения quantization, gpu_memory_utilization range.

- [ ] **Unit: LoRA registry.** Тесты CRUD адаптеров, LRU eviction, concurrent access.

- [ ] **Unit: model routing.** Тесты автовыбора модели: text-only → Qwen, image → SmolVLM2, explicit header override.

- [ ] **Integration: API.** Тесты OpenAI-совместимых эндпоинтов: chat completions (streaming + non-streaming), tool calling, structured output. Требует GPU или mock engine.

- [ ] **Integration: multimodal.** Тесты image + text input, video input, scene analysis endpoint.
