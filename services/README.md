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

## Как вносить изменения в субмодули

1. Перейди в нужный сабмодуль:

```bash
cd services/<имя_сервиса>
```

2. Убедись, что ты на правильной ветке, подтяни свежую историю и сделай свои правки:

```bash
git checkout <branch>
git pull --ff-only
# внеси изменения, запусти тесты
git add .
git commit -m "описание изменений"
git push origin <branch>
```

3. Вернись в корень метарепозитория и обнови gitlink сабмодуля:

```bash
cd - # вернуться в корень
git checkout dev   # если нужно
git add services/<имя_сервиса>
git commit -m "Update <имя_сервиса> submodule"
git push origin dev
```

4. Для других разработчиков: синхронизируй сабмодули после обновления метарепозитория:

```bash
git checkout dev
git pull
git submodule sync --recursive
git submodule update --remote --merge
```
