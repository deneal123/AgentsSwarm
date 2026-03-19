## Описание

Сервис для локального запуска NVIDIA Isaac Sim (GUI или headless) в Docker с сохранением кешей/конфигов на хосте. В комплекте: compose-файлы, Makefile, скрипты запуска и шаблон переменных окружения.

## Что нужно

- Драйвер NVIDIA + установленный [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- Docker + Docker Compose (v2)
- X11 сервер, если хотите GUI (например, обычный рабочий стол на Linux)

Для автоматизации установки зависимостей можно выполнить:

```bash
bash ./scripts/start_prerequisites.sh
```

## Быстрый старт

1. Создайте файл окружения и при необходимости поправьте значения:

```bash
make env
```

Ключевые переменные в `.env`:
- `IMAGE` — тег образа Isaac Sim (по умолчанию `nvcr.io/nvidia/isaac-sim:5.1.0`)
- `ISAAC_ROOT` — папка на хосте для кешей/конфигов/логов (`./tmp` по умолчанию)
- `CONTAINER_NAME` — базовое имя контейнера
- `ISAAC_USER` — пользователь внутри контейнера (по умолчанию `0:0`, чтобы скрипты Isaac Sim были читаемы)
- `DISPLAY` — для GUI, если нужно переопределить

2. Запуск в headless режиме (без окна):

```bash
make headless
```

3. Запуск с GUI:

```bash
make gui
```

4. Остановить контейнеры:

```bash
make stop-headless
make stop-gui
```

5. Логи:

```bash
make logs-headless
make logs-gui
```

6. Быстрая проверка совместимости (запускает `isaac-sim.compatibility_check.sh` внутри контейнера):

```bash
make check
```

7. Очистить кеши/логи (папка `tmp/`):

```bash
make clean
```

## Альтернативный запуск через скрипты

Скрипт сам подтянет `.env` (если есть), создаст необходимые папки и выставит права.

- Headless: `./scripts/start_isaac.sh headless <PATH_TO_ROOT>`
- GUI: `DISPLAY=:0 ./scripts/start_isaac.sh gui <PATH_TO_ROOT>`
- Проверка: `./scripts/start_isaac.sh check <PATH_TO_ROOT>`

`<PATH_TO_ROOT>` можно опустить — тогда используется `ISAAC_ROOT` из `.env` или папка со скриптом.

## Файлы

- `Makefile` — цели для запуска/остановки контейнеров, логов, проверки и очистки
- `.env.example` — шаблон окружения
- `docker/isaac.headless.yml` — конфигурация для headless режима
- `docker/isaac.gui.yml` — конфигурация для GUI режима
- `scripts/start_isaac.sh` — универсальный запуск/проверка в Docker
- `scripts/start_prerequisites.sh` — установка зависимостей (Docker, NVIDIA Toolkit, Isaac ROS repo)

## Советы по GUI

- Перед стартом можно открыть доступ X11: `xhost +local:root`
- Переменная `DISPLAY` должна совпадать с вашей сессией (обычно `:0`)
- Файл `~/.Xauthority` должен существовать и быть читаемым

## Удалённый GUI без локального дисплея (TurboVNC + VirtualGL)

Если сервер без X-сессии, используйте VNC с аппаратным ускорением:

1. Установить пакеты (Ubuntu, через официальный репозиторий TurboVNC/VirtualGL):
	```bash
	sudo apt update && sudo apt install -y wget gnupg lsb-release
	wget https://dist.turbovnc.org/apt/turbovnc-apt-key.pub
	sudo gpg --dearmor -o /usr/share/keyrings/turbovnc.gpg turbovnc-apt-key.pub
	echo "deb [signed-by=/usr/share/keyrings/turbovnc.gpg] https://dist.turbovnc.org/apt/$(lsb_release -sc) $(lsb_release -sc) main" | \
	sudo tee /etc/apt/sources.list.d/turbovnc.list
	sudo apt update
	sudo apt install -y turbovnc virtualgl
	```
	Если репозиторий недоступен для вашей версии, скачайте `.deb` с https://github.com/VirtualGL/virtualgl/releases и https://github.com/TurboVNC/turbovnc/releases и установите `sudo dpkg -i <pkg>.deb && sudo apt -f install`.
    Возможно понадобятся:
    `sudo apt install -y libglu1-mesa libegl1-mesa`
    `sudo apt install -y libglu1-mesa:amd64 libegl1-mesa:amd64`
    `sudo apt install -y lightdm`
    `sudo service sddm stop`
    `sudo service lightdm start`

2. Настроить VirtualGL (GPU-доступ):
	```bash
	sudo /opt/VirtualGL/bin/vglserver_config -config +s +f
	sudo systemctl restart docker
	```
3. Запустить VNC-сервер (пример на дисплее :1):
	```bash
	/opt/TurboVNC/bin/vncserver -localhost -geometry 1920x1080 :1
	```
4. Прописать `DISPLAY=:1` в `.env` и запустить GUI контейнер:
	```bash
	make gui   # или sudo make gui
	```
5. С ноутбука подключиться через SSH туннель и VNC-клиент:
	```bash
	ssh -L 5901:localhost:5901 user@server
	# затем открыть VNC-клиент на localhost:5901 (пароль задаётся при первом vncserver)
	```
6. Для 3D-ускорения внутри VNC-сессии можно использовать `vglrun` при запуске приложений, но Isaac Sim уже использует GPU; главное — `DISPLAY` совпадает с VNC дисплеем.

Если нужен рабочий стол внутри VNC, установите лёгкую DE (например `xfce4`) и добавьте в `~/.vnc/xstartup.turbovnc` строку `xfce4-session &`, затем перезапустите `vncserver`.

## Полезные каталоги на хосте

`ISAAC_ROOT` содержит:
- `cache/` — кеши Omniverse/ComputeCache
- `config/` — пользовательские настройки Isaac Sim
- `data/` и `pkg/` — данные и установленные пакеты
- `logs/` — логи симуляции
