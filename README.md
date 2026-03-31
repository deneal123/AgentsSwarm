# Nvidia Isaac Sim

## Создание .env файла

Перед запуском необходимо создать файл .env в директории ./IsaacSim/tools/docker/ (рядом с docker-compose.yml):

```bash
# Перейдите в директорию с docker-compose.yml
cd ./IsaacSim/tools/docker

# Создайте .env файл
cat > .env << 'EOF'
# Docker образ Isaac Sim
ISAAC_SIM_IMAGE=nvcr.io/nvidia/isaac-sim:6.0.0-dev2

# Хост для WebRTC стриминга
ISAACSIM_HOST=127.0.0.1

# Порты WebRTC
ISAACSIM_SIGNAL_PORT=49100
ISAACSIM_STREAM_PORT=47998

# Порт веб-просмотрщика
WEB_VIEWER_PORT=8210

# GPU устройство (0 - для одной GPU, all - для всех)
GPU_DEVICE=all

# Путь для хранения данных (укажите абсолютный путь)
ISAAC_SIM_DATA=/root/docker/isaac-sim
EOF
```

## Запуск контейнера

```bash
# Вернитесь в корневую директорию Isaac Sim
cd ./IsaacSim

# Запустите сборку и контейнер
docker compose -p isim -f tools/docker/docker-compose.yml up --build -d
```

## Проверка работы

```bash
# Просмотр всех логов
docker compose -p isim logs

# Просмотр логов веб-просмотрщика (покажет URL)
docker compose -p isim logs web-viewer

# Просмотр логов Isaac Sim (ищите "app ready")
docker compose -p isim logs isaac-sim

# Отслеживание логов в реальном времени (Ctrl+C для выхода)
docker compose -p isim logs -f
```

## Остановка контейнера

```bash
# Остановка и удаление контейнеров с volumes
docker compose -p isim down -v

# Очистка кэша сборки и неиспользуемых данных
docker builder prune -a -f
docker volume prune -f
```

## Важные замечания

- Размер образа: Для загрузки образа требуется 10+ ГБ свободного места
- Абсолютные пути: В переменной ISAAC_SIM_DATA используйте полный абсолютный путь (символ ~ не раскрывается Docker Compose)
- GPU: Убедитесь, что установлен NVIDIA Container Toolkit для работы с GPU
- Доступ в браузере: После запуска веб-просмотрщик будет доступен по адресу: http://localhost:8210