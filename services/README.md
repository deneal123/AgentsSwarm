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
