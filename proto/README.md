# Proto — Protobuf контракты AgentsSwarm

Этот каталог содержит все Protobuf-определения для межсервисного взаимодействия через gRPC.

---

## Структура

```
proto/
├── buf.yaml                          # buf v2 конфигурация модуля
├── buf.gen.yaml                      # конфигурация генерации кода
├── scripts/
│   └── gen-proto.sh                  # локальная генерация через grpcio-tools
├── common/
│   └── v1/
│       ├── types.proto               # общие типы (enums, Position, BoundingBox)
│       └── telemetry.proto           # RobotTelemetry, SensorData, RobotEvent
├── gateway/
│   └── v1/
│       └── gateway.proto             # AuthService, NotificationService
├── orchestrator/
│   └── v1/
│       └── orchestrator.proto        # OrchestratorService (SubmitCommand, StreamEvents)
└── inference/
    └── v1/
        ├── triton.proto              # TritonInferenceService (DetectObjects, TrackObjects)
        ├── vllm.proto                # VLLMService (Generate, StreamGenerate, AnalyzeImage)
        └── smolvla.proto             # SmolVLAService (PredictAction, StreamActions)
```

---

## Генерация кода

### Способ 1: через buf (рекомендуется)

Требует авторизации в buf registry (`buf registry login`).

```bash
cd proto/
buf generate
```

Генерирует:
- **Python** (`*_pb2.py`, `*_pb2.pyi`, `*_pb2_grpc.py`) → в каждый микросервис
- **TypeScript** (ConnectRPC, `*.ts`) → `services/frontend/src/proto/`

### Способ 2: локально через grpcio-tools

Не требует buf registry. Нужен Python с `grpcio-tools` и `mypy-protobuf`.

```bash
cd /root/projects/AgentsSwarm
bash proto/scripts/gen-proto.sh

# Только Python стабы:
bash proto/scripts/gen-proto.sh --python-only

# Только TypeScript:
bash proto/scripts/gen-proto.sh --ts-only

# Без .pyi стабов:
bash proto/scripts/gen-proto.sh --no-pyi
```

### Через Makefile

```bash
make proto           # buf generate (если buf установлен)
make proto-local     # через grpcio-tools
```

---

## Зависимости

### Для buf генерации:

```bash
# Установка buf CLI
curl -sSL https://github.com/bufbuild/buf/releases/latest/download/buf-Linux-x86_64 \
    -o /usr/local/bin/buf && chmod +x /usr/local/bin/buf

# Авторизация (опционально для публичных плагинов)
buf registry login
```

### Для локальной генерации Python:

```bash
pip install grpcio-tools mypy-protobuf
```

### Для TypeScript (ConnectRPC):

```bash
npm install -g @bufbuild/protoc-gen-es @connectrpc/protoc-gen-connect-es
# Frontend зависимости:
# @connectrpc/connect @connectrpc/connect-web @bufbuild/protobuf
```

---

## Проверка proto-файлов

```bash
cd proto/
buf lint                    # проверка стиля и корректности
buf breaking --against .git # проверка на breaking changes
```

---

## Добавление нового proto-файла

1. Создайте файл `proto/<service>/v1/<service>.proto`
2. Добавьте output targets в `buf.gen.yaml` для нужных сервисов
3. Добавьте файл в список `PROTO_FILES` в `scripts/gen-proto.sh`
4. Запустите генерацию: `cd proto && buf generate`
5. Скоммитьте и `.proto` файл, и сгенерированные `*_pb2*.py` файлы

---

## Соглашения

| Правило | Пример |
|---------|--------|
| Имена пакетов: `<service>.v<n>` | `common.v1`, `inference.v1` |
| Enum values: `SCREAMING_SNAKE_CASE` с префиксом | `ROBOT_STATUS_IDLE` |
| Message names: `PascalCase` | `RobotTelemetry` |
| RPC names: `PascalCase`, глагол + существительное | `SubmitCommand`, `StreamEvents` |
| Field numbers: не изменять после публикации | — |
| Deprecated fields: помечать `deprecated = true`, не удалять | — |
| Well-known types: использовать `google.protobuf.Timestamp` вместо `int64` | — |

---

## Совместимость

Все изменения proto-файлов проверяются на **backward compatibility** через `buf breaking` в CI/CD pipeline (этап 5).

**Нельзя** (breaking changes):
- Изменять номера полей
- Переименовывать пакет или service
- Удалять поля или RPC методы
- Изменять типы полей

**Можно** (non-breaking):
- Добавлять новые поля (с новыми номерами)
- Добавлять новые RPC методы
- Добавлять новые enum значения
- Помечать поля как `deprecated`
