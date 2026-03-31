
# SmolVLA Model Optimization Framework

Фреймворк для оптимизации моделей SmolVLA (Vision-Language-Action) для робототехнических приложений с использованием дистилляции знаний, квантизации и других методов оптимизации.

## Отчёты

- [Отчёт №1](https://github.com/deneal123/AgentsSwarm/tree/smolvla_tools/docs/report_1.md)
- [Отчёт №2](https://github.com/deneal123/AgentsSwarm/tree/smolvla_tools/docs/report_2.md)
- [Отчёт №3](https://github.com/deneal123/AgentsSwarm/tree/smolvla_tools/docs/report_3.md)

## Возможности

- **Дистилляция знаний**: Архитектура учитель-ученик с расширенными функциями потерь
- **Сжатие модели**: Уменьшение размера до 85% (сжатие в 6.8 раза)
- **Оптимизация скорости**: Ускорение инференса в 20–25 раз
- **Смешанная точность**: Поддержка FP16 для ускоренного обучения
- **Экспорт в ONNX**: Готовность к промышленному развертыванию
- **Улучшенная архитектура**: CNN-энкодер + Transformer с позиционным кодированием
- **Продвинутая дистилляция**: Многокомпонентная функция потерь с передачей внимания
- **Оценка на реальных датасетах**: Интеграция с LeRobot
- **Комплексный мониторинг**: Детальные метрики обучения и ранняя остановка

## Установка

```bash
# Установка зависимостей через uv
uv sync

# Или установка через pip
pip install -e .
```

## Быстрый старт

### Базовое обучение

```bash
# Обучение SmolVLA с интеграцией HuggingFace
python scripts/train.py --epochs 10 --dataset lerobot/pusht

# Быстрый тест на небольшом датасете
python scripts/train.py --epochs 5 --num_samples 500 --batch_size 16

# Полный пайплайн оптимизации
python scripts/train.py --epochs 20 --profile --quantize --prune --mixed_precision
```

### Расширенные опции обучения

```bash
# Включение профилирования и анализа оптимизации
python scripts/train.py --epochs 10 --profile --quantize --prune

# Смешанная точность с профилированием
python scripts/train.py --epochs 15 --mixed_precision --profile

# Обучение на пользовательском датасете
python scripts/train.py --dataset lerobot/aloha_static_coffee --model_id lerobot/smolvla_base

# Полный пайплайн оптимизации с настройками датасета
python scripts/train.py --epochs 20 --profile --quantize --prune --mixed_precision \
  --dataset_cache_dir ./my_datasets --dataset_percentage 0.1

# Использование переменных окружения
export HF_DATASETS_CACHE="./datasets_cache"
export DATASET_DOWNLOAD_PERCENTAGE="0.5"
python scripts/train.py --epochs 10
```

## Экспорт и развертывание

```bash
# Экспорт обученной модели в ONNX
python scripts/export_onnx.py --model_path results/best_model.pth
```

## Аргументы командной строки

| Аргумент | Описание | По умолчанию |
| --- | --- | --- |
| --model_id | Идентификатор модели в HuggingFace | lerobot/smolvla_base |
| --dataset | Название датасета | lerobot/pusht |
| --epochs | Количество эпох обучения | 10 |
| --batch_size | Размер батча | 32 |
| --num_samples | Количество обучающих семплов | 2000 |
| --lr | Скорость обучения | 1e-4 |
| --student_ratio | Соотношение размера модели-ученика (0.1–0.9) | 0.5 |
| --temperature | Температура дистилляции | 3.0 |
| --alpha | Вес функции потерь дистилляции | 0.7 |
| --mixed_precision | Включить смешанную точность | False |
| --profile | Включить профилирование производительности | False |
| --quantize | Анализ потенциала квантизации | False |
| --prune | Анализ потенциала прунинга | False |
| --dataset_cache_dir | Директория кэша датасета | None |
| --dataset_percentage | Процент датасета (0.0–1.0) | None |
| --output_dir | Директория для результатов | results/real_optimization |

## Конфигурация

### Переменные окружения

Создайте файл .env из .env.example для настройки проекта:

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование файла .env
```

## Ключевые переменные окружения:

| Переменная | Описание
| --- | ---
| HF_DATASETS_CACHE | Директория кэша датасетов
| DATASET_DOWNLOAD_PERCENTAGE | Доля используемого датасета (0.01–1.0)
| SMOLVLA_MODEL_ID | Идентификатор модели SmolVLA по умолчанию
| DEFAULT_EPOCHS | Количество эпох обучения по умолчанию
| DEFAULT_BATCH_SIZE | Размер батча по умолчанию
| DEFAULT_LEARNING_RATE | Скорость обучения по умолчанию
| ENABLE_MIXED_PRECISION | Включить обучение в FP16
| ENABLE_PROFILING | Включить профилирование


## T_DIR Директория для результатов по умолчанию


## Пример использования

1. Базовое обучение

```python
from smolvla_tools.training import Trainer
from smolvla_tools.models import TeacherModel, StudentModel

# Инициализация моделей
teacher = TeacherModel.from_pretrained("lerobot/smolvla_base")
student = StudentModel(teacher.config, ratio=0.5)

# Создание тренера
trainer = Trainer(
    teacher=teacher,
    student=student,
    dataset_name="lerobot/pusht",
    batch_size=32,
    learning_rate=1e-4,
    temperature=3.0,
    alpha=0.7
)

# Запуск обучения
trainer.train(epochs=10)
```

2. Оптимизация и профилирование

```python
from smolvla_tools.optimization import optimize_model

# Полная оптимизация
optimized_model = optimize_model(
    model_path="results/best_model.pth",
    quantize=True,
    prune=True,
    profile=True
)

# Сохранение оптимизированной модели
optimized_model.save("results/optimized_model")
```

3. Экспорт в ONNX

```python
from smolvla_tools.export import export_to_onnx

export_to_onnx(
    model_path="results/optimized_model",
    output_path="results/model.onnx",
    input_shape=(1, 3, 224, 224)
)
```

## Результаты оптимизации

Метрика До оптимизации После оптимизации Улучшение
Размер модели 1.2 GB 180 MB 6.8×
Время инференса 450 ms 18 ms 25×
Точность 87.3% 85.1% -2.2%
Потребление памяти 3.8 GB 512 MB 7.4×

## Требования к системе

- Python 3.10 или выше
- CUDA 11.8+ (для GPU)
- 16 GB RAM (рекомендуется 32 GB)
- 8 GB VRAM (для обучения)
