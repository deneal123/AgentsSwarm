# services/

Здесь располагаются git submodules всех микросервисов.

Инициализация после клонирования мета-репозитория:

```bash
git submodule update --init --recursive
```

Обновление до последних коммитов:

```bash
git submodule update --remote --merge
```

| Директория | Описание |
|---|---|
| `gateway_service/` | API-шлюз (FastAPI, JWT, WebSocket) |
| `orchestrator/` | Оркестратор роя (LangGraph, Celery, Agents SDK) |
| `vllm_service/` | LLM + мультимодальный инференс (vLLM) |
| `triton_inference/` | Компьютерное зрение (NVIDIA Triton, YOLO, ByteTrack) |
| `smolvla_service/` | Vision-Language-Action модели (LeRobot) |
| `communication_service/` | Мост MQTT ↔ RabbitMQ (EMQX, paho, pika) |
| `robot_edge/` | Борт робота (ROS 2 Jazzy, Edge AI Proxy, SmolVLA Edge) |
| `frontend/` | Веб-интерфейс оператора (React, TypeScript, Three.js) |
