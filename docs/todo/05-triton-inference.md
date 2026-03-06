# TODO: Triton Inference

Микросервис компьютерного зрения на NVIDIA Triton Inference Server. Детекция, трекинг, сегментация, ensemble-пайплайны.

---

## Этап 1 — Инициализация проекта

- [ ] **Создать репозиторий triton_inference.** Poetry-проект с зависимостями: tritonclient[all], fastapi, uvicorn, pydantic-settings, numpy, opencv-python-headless, ultralytics, prometheus-client, structlog.

- [ ] **Настроить .pre-commit-config.yaml.** Хуки: ruff, mypy, bandit.

- [ ] **Создать Dockerfile.** Базовый образ `nvcr.io/nvidia/tritonserver:24.09-py3`. Установка Python-обёртки, копирование model_repository. HEALTHCHECK через Triton health API (порт 8000 /v2/health/ready).

- [ ] **Создать config.py.** Pydantic Settings: MODEL_REPOSITORY_PATH, TRITON_HTTP_PORT (8000), TRITON_GRPC_PORT (8001), TRITON_METRICS_PORT (8002), MODEL_CONTROL_MODE (poll/explicit), BATCH_SIZE, MAX_QUEUE_DELAY_MS, LOG_LEVEL, JAEGER_ENDPOINT.

- [ ] **Создать main.py.** Entrypoint: запуск Triton Server как subprocess + FastAPI wrapper для кастомных эндпоинтов. Health proxy.

---

## Этап 2 — Model Repository

- [ ] **YOLO detector (model_repository/yolo_detector/).** config.pbtxt: platform onnxruntime, input (IMAGE: fp32 [3,640,640]), output (DETECTIONS: fp32 [N,6]). Dynamic batching: preferred_batch_size [1,4,8], max_queue_delay 5000μs.

- [ ] **Конвертация YOLO в ONNX.** Скрипт convert_model.py: загрузка ultralytics YOLO модели → export в ONNX (opset 17, dynamic axes) → опционально TensorRT engine. Поддержка YOLOv8 и YOLO26.

- [ ] **ByteTrack model (model_repository/bytetrack/).** config.pbtxt: Python backend, вход — детекции текущего + предыдущего кадра, выход — tracked objects с persistent IDs.

- [ ] **Depth estimation model (model_repository/depth_estimator/).** config.pbtxt: ONNX model (MiDaS/DPT), вход — RGB image, выход — depth map. Используется для оценки расстояния до объектов.

- [ ] **Ensemble pipeline (model_repository/ensemble_detect_track/).** config.pbtxt: ensemble scheduling, шаги: yolo_detector → bytetrack. Вход: изображение, выход: tracked detections с IDs.

- [ ] **Instance groups.** Конфигурация instance_group в config.pbtxt: count=2 per GPU для YOLO (параллельный inference), count=1 для ByteTrack (CPU-bound).

---

## Этап 3 — Python Wrapper API

- [ ] **Detection endpoint (api/detect.py).** POST /detect — приём изображения (base64 или binary), вызов Triton gRPC yolo_detector, возврат JSON: list[BoundingBox] с class_id, confidence, x1y1x2y2.

- [ ] **Tracking endpoint (api/track.py).** POST /track — приём изображения + session_id (для persistent tracking), вызов ensemble_detect_track, возврат tracked objects с track_id.

- [ ] **Batch detection endpoint.** POST /detect/batch — приём нескольких изображений, формирование батча, один вызов Triton → результаты для каждого изображения.

- [ ] **Streaming detection.** gRPC server-side streaming: клиент отправляет поток кадров, сервер возвращает поток детекций. Для real-time видео с роботов.

- [ ] **Health proxy (api/health.py).** GET /health → Triton /v2/health/live, GET /ready → Triton /v2/health/ready, GET /models → Triton /v2/models (список загруженных моделей и их статус).

---

## Этап 4 — Preprocessing

- [ ] **Image preprocessing (preprocessing/image.py).** Ресайз до target_size (640×640 для YOLO), нормализация [0,1], CHW transpose, batch dimension. Поддержка: numpy array, bytes, PIL Image, base64 string.

- [ ] **Letterbox padding.** Сохранение aspect ratio при ресайзе: padding серым цветом, сохранение scale factor и offset для обратного преобразования координат.

- [ ] **Video preprocessing (preprocessing/video.py).** Декодирование видео (opencv), извлечение кадров с заданным FPS, формирование батча кадров.

---

## Этап 5 — Postprocessing

- [ ] **NMS (postprocessing/nms.py).** Non-Maximum Suppression: фильтрация overlapping boxes по IoU threshold (0.45), confidence threshold (0.25). Поддержка class-specific NMS.

- [ ] **Coordinate rescaling.** Обратное преобразование координат bbox из model space (640×640) в original image space с учётом letterbox padding.

- [ ] **Tracking postprocessing (postprocessing/tracking.py).** Интеграция ByteTrack результатов: присвоение track_id, фильтрация коротких треков (min_track_length), smoothing bbox coordinates.

- [ ] **Result serialization.** Формирование структурированного ответа: list[Detection] с полями: track_id, class_name, confidence, bbox (normalized + pixel), timestamp.

- [ ] **Feature Store update.** После каждого inference — запись результатов в Redis Feature Store: `detections:{robot_id}:latest` (Hash), `detections:{robot_id}:history` (Stream).

---

## Этап 6 — Оптимизация

- [ ] **TensorRT конвертация.** Скрипт: ONNX → TensorRT engine с FP16 precision. Benchmark: сравнение latency ONNX vs TensorRT. Ожидаемое ускорение 2-3×.

- [ ] **Dynamic batching tuning.** Тестирование preferred_batch_size [1,2,4,8,16], max_queue_delay [1000,5000,10000]μs. Выбор оптимальной конфигурации для target latency <50ms.

- [ ] **Model warmup.** Конфигурация model_warmup в config.pbtxt: прогрев модели при загрузке фейковыми данными для инициализации CUDA kernels.

- [ ] **Memory optimization.** Pinned memory для input/output tensors (shared_memory в Triton). Сокращение CPU↔GPU transfers.

- [ ] **Benchmark script (scripts/benchmark.py).** Автоматический бенчмарк: latency p50/p95/p99, throughput (images/sec), GPU utilization для разных batch sizes и моделей.

---

## Этап 7 — Тесты

- [ ] **conftest.py.** Фикстуры: sample images (640×640 test patterns), mock Triton client, sample detection results, sample tracking sessions.

- [ ] **Unit: preprocessing.** Тесты ресайз, letterbox padding, нормализация, batch formation для разных input форматов.

- [ ] **Unit: postprocessing.** Тесты NMS (overlapping boxes, edge cases), coordinate rescaling, result serialization.

- [ ] **Unit: config.pbtxt validation.** Проверка всех config.pbtxt: корректные input/output dimensions, dynamic batching params, instance groups.

- [ ] **Integration: Triton.** Тесты с реальным Triton Server (testcontainers + GPU): загрузка модели, single inference, batch inference, ensemble pipeline.

- [ ] **Integration: tracking session.** Тест multi-frame tracking: серия кадров → persistent track_ids → корректные trajectory.
