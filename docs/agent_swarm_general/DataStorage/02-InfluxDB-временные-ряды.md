# InfluxDB — Временные ряды

## Роль

InfluxDB используется для хранения телеметрии роботов, метрик системных компонентов и событий со временем. Поддерживает агрегацию, downsampling и ретеншн-политики.

---

## Дизайн измерений

- measurement: `robot_telemetry`
- tags: `robot_id`, `component`, `zone`
- fields: `battery`, `speed`, `temperature`, `error_code`
- timestamp: unix epoch в наносекундах

---

## Retention и downsampling

- Горячие данные: retention 7 дней с full resolution
- Среднесрочные: agg (1m, 5m) — retention 30 дней
- Долгосрочные: agg (1h) — retention 1 год

---

## Интеграция

- Collector (Telegraf/Prometheus exporters) для отправки метрик
- Запросы для Grafana — готовые дашборды для состояния роботов и GPU
