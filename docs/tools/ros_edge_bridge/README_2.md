# План занятия 2: Виртуальная среда разработки

## Цели занятия

### Обучающие:
- Понять структуру и назначение Dockerfile
- Освоить работу с VS Code и удаленным подключением к контейнеру
- Познакомить с системой сборки colcon
- Создать первый ROS 2 workspace и узел

### Развивающие:
- Развить навыки работы с командной строкой
- Сформировать понимание структуры ROS 2 проекта
- Освоить современные инструменты разработки

### Воспитательные:
- Развить самостоятельность в решении технических проблем
- Укрепить навыки работы в команде
- Сформировать культуру разработки

---

## Структура занятия

### 1. Проверка домашнего задания и запуск контейнера

#### 1.1 Быстрая проверка
- Кто скачал Dockerfile и запустил контейнер?
- У кого возникли проблемы?
- Кто попробовал команды Linux?

#### 1.2 Запуск контейнера для тех, кто не сделал

**Быстрая инструкция:**

```bash
# Создаем директорию проекта
mkdir -p ~/robotics_course
cd ~/robotics_course

# Скачиваем Dockerfile (если еще не сделали)
# Кладем файл Dockerfile.vnc в эту папку

# Собираем образ
docker build -f Dockerfile.vnc -t ros2_course:v1 .

# Запускаем контейнер
docker run -d \
    --name ros2_dev \
    -p 6080:6080 \
    -p 5901:5901 \
    -v ~/robotics_course/ros2_ws:/home/student/ros2_ws \
    ros2_course:v1

# Проверяем, что контейнер запущен
docker ps | grep ros2_dev
```

**Доступ к рабочему столу:**
- Открыть браузер: http://localhost:6080/vnc.html
- Пароль: `student`

#### 1.3 Решение типичных проблем

**Проблемы с Docker:**
- Docker не запускается → проверить виртуализацию в BIOS
- Порты заняты → изменить порты: `-p 6081:6080`
- Нет прав доступа → `sudo usermod -aG docker $USER` и перезагрузка

**Проблемы с VNC:**
- Не открывается браузер → проверить, что контейнер запущен
- Черный экран → подождать 30 секунд, обновить страницу
- Не работает клавиатура → проверить раскладку

**План для отстающих:**
- Работают в паре с тем, у кого запущено
- После занятия индивидуальная помощь
- Есть запасные ноутбуки с предустановленным окружением

---

### 2. Разбор Dockerfile

Теперь давайте подробно разберем, что находится в Dockerfile, который вы запустили.

#### 2.1 Базовый образ и переменные окружения

```dockerfile
FROM osrf/ros:jazzy-desktop-full
```

**Что это значит:**
- `FROM` - указывает базовый образ, на основе которого мы строим свой
- `osrf/ros:jazzy-desktop-full` - официальный образ ROS 2 Jazzy с полным набором инструментов
- Jazzy - последняя версия ROS 2 (май 2024)
- `desktop-full` - включает GUI инструменты: RViz, rqt, Gazebo

**Переменные окружения:**

```dockerfile
ENV DEBIAN_FRONTEND=noninteractive \
    ROS_DISTRO=jazzy \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8
```

**Объяснение:**
- `ENV` - устанавливает переменные окружения
- `DEBIAN_FRONTEND=noninteractive` - отключает интерактивные запросы при установке пакетов
- `ROS_DISTRO=jazzy` - определяет версию ROS 2
- `LANG` и `LC_ALL` - настраивают локаль на UTF-8 (поддержка русского языка)

#### 2.2 Установка пакетов

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    vim \
    nano \
    sudo \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-numpy \
    python3-matplotlib \
    python3-opencv \
    # VNC и Desktop окружение
    tigervnc-standalone-server \
    tigervnc-common \
    novnc \
    websockify \
    xfce4 \
    xfce4-terminal \
    # ...остальные пакеты
```

**Разбор по блокам:**

**Базовые инструменты разработки:**
- `build-essential` - компиляторы C/C++ (gcc, g++, make)
- `git` - система контроля версий
- `vim`, `nano` - текстовые редакторы
- `sudo` - выполнение команд от имени root

**Python и научные библиотеки:**
- `python3-pip` - менеджер пакетов Python
- `python3-colcon-common-extensions` - система сборки для ROS 2
- `python3-rosdep` - управление зависимостями ROS
- `python3-numpy` - работа с массивами и матрицами
- `python3-matplotlib` - построение графиков
- `python3-opencv` - компьютерное зрение

**VNC сервер (удаленный рабочий стол):**
- `tigervnc-standalone-server` - VNC сервер (передает экран по сети)
- `tigervnc-common` - общие файлы VNC
- `novnc` - доступ к VNC через браузер (веб-интерфейс)
- `websockify` - прокси WebSocket для noVNC
- `xfce4` - легкий графический рабочий стол
- `xfce4-terminal` - терминал для XFCE
- `dbus-x11` - коммуникация между приложениями
- `autocutsel` - синхронизация буфера обмена

**Шрифты:**
- `xfonts-base` - базовые шрифты
- `xfonts-100dpi`, `xfonts-75dpi` - шрифты разных разрешений
- `xfonts-cyrillic` - кириллические шрифты (русский язык)

**ROS 2 инструменты:**
```dockerfile
ros-${ROS_DISTRO}-rqt* \
ros-${ROS_DISTRO}-rviz2 \
ros-${ROS_DISTRO}-teleop-twist-keyboard \
ros-${ROS_DISTRO}-tf2-tools \
ros-${ROS_DISTRO}-foxglove-bridge \
```

- `rqt*` - графические инструменты для отладки (графики, логи, топики)
- `rviz2` - 3D визуализация роботов и данных сенсоров
- `teleop-twist-keyboard` - управление роботом с клавиатуры
- `tf2-tools` - работа с системами координат
- `foxglove-bridge` - подключение к Foxglove Studio

**Зачем `rm -rf /var/lib/apt/lists/*`?**
- Удаляет кэш apt для уменьшения размера образа
- После установки пакетов этот кэш не нужен

#### 2.3 Установка Foxglove Studio

```dockerfile
RUN wget --timeout=30 --tries=3 -q \
    https://github.com/foxglove/studio/releases/latest/download/foxglove-studio-latest-linux-amd64.deb \
    -O /tmp/foxglove.deb || true && \
    if [ -f /tmp/foxglove.deb ] && [ -s /tmp/foxglove.deb ]; then \
        apt-get update && \
        apt-get install -y /tmp/foxglove.deb || echo "Foxglove Studio installation failed (expected on ARM)" && \
        rm /tmp/foxglove.deb && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        echo "Foxglove Studio download skipped (not available for this architecture)"; \
    fi
```

**Что происходит:**
1. `wget` - скачивает .deb файл Foxglove Studio с GitHub
2. `--timeout=30 --tries=3` - таймаут 30 секунд, 3 попытки
3. `|| true` - не прерывать сборку при ошибке
4. `if [ -f ... ] && [ -s ... ]` - проверка, что файл существует и не пустой
5. `apt-get install -y /tmp/foxglove.deb` - установка .deb пакета
6. `|| echo "..."` - вывод сообщения при ошибке (например, на ARM процессорах)

**Зачем Foxglove Studio:**
- Современная альтернатива RViz
- Веб-интерфейс для визуализации данных робота
- Графики, 3D модели, логи в одном окне

#### 2.4 Создание пользователя

```dockerfile
ARG USERNAME=student
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN (groupadd --gid $USER_GID $USERNAME 2>/dev/null || \
     groupmod -n $USERNAME $(getent group $USER_GID | cut -d: -f1)) \
    && (useradd --uid $USER_UID --gid $USER_GID -m $USERNAME 2>/dev/null || \
        usermod -l $USERNAME -d /home/$USERNAME -m $(getent passwd $USER_UID | cut -d: -f1)) \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME
```

**Что такое ARG:**
- `ARG` - переменные для сборки образа (можно переопределить при `docker build`)
- `USERNAME=student` - имя пользователя
- `USER_UID=1000` - ID пользователя (обычно 1000 для первого пользователя)
- `USER_GID` - ID группы (такой же как UID)

**Зачем создавать пользователя:**
- По умолчанию Docker работает от root (небезопасно)
- Файлы, созданные в контейнере, будут принадлежать вашему пользователю на хосте
- UID 1000 обычно совпадает с вашим пользователем на Linux/Mac

**Логика создания:**
1. Пытается создать группу с GID 1000
2. Если группа существует, переименовывает ее в "student"
3. Пытается создать пользователя с UID 1000
4. Если пользователь существует, переименовывает его в "student"
5. Дает пользователю sudo права без пароля

**Переключение на пользователя:**
```dockerfile
USER $USERNAME
WORKDIR /home/$USERNAME
```
- `USER` - все последующие команды выполняются от имени student
- `WORKDIR` - устанавливает рабочую директорию

#### 2.5 Создание workspace

```dockerfile
RUN mkdir -p ros2_ws/src
```

**Структура ROS 2 workspace:**
```
ros2_ws/
├── src/           # Исходный код пакетов (здесь мы пишем код)
├── build/         # Временные файлы сборки (создается colcon build)
├── install/       # Установленные пакеты (создается colcon build)
└── log/           # Логи сборки (создается colcon build)
```

#### 2.6 Настройка VNC

```dockerfile
RUN mkdir -p ~/.vnc && \
    echo "student" | vncpasswd -f > ~/.vnc/passwd && \
    chmod 600 ~/.vnc/passwd
```

**Что делает:**
- Создает директорию для конфигурации VNC
- Устанавливает пароль "student" для VNC
- `vncpasswd -f` - создает зашифрованный пароль
- `chmod 600` - только владелец может читать файл (безопасность)

**Startup скрипт VNC:**
```dockerfile
RUN echo '#!/bin/bash' > ~/.vnc/xstartup && \
    echo 'export XKL_XMODMAP_DISABLE=1' >> ~/.vnc/xstartup && \
    echo 'unset SESSION_MANAGER' >> ~/.vnc/xstartup && \
    echo 'unset DBUS_SESSION_BUS_ADDRESS' >> ~/.vnc/xstartup && \
    echo '# Clipboard sync' >> ~/.vnc/xstartup && \
    echo 'autocutsel -fork' >> ~/.vnc/xstartup && \
    echo 'autocutsel -selection PRIMARY -fork' >> ~/.vnc/xstartup && \
    echo 'exec startxfce4' >> ~/.vnc/xstartup && \
    chmod +x ~/.vnc/xstartup
```

**Объяснение xstartup:**
- `#!/bin/bash` - скрипт выполняется в bash
- `export XKL_XMODMAP_DISABLE=1` - отключает xmodmap (конфликтует с некоторыми раскладками)
- `unset SESSION_MANAGER` - отключает менеджер сессий
- `autocutsel -fork` - синхронизирует буфер обмена между VNC и локальной машиной
- `exec startxfce4` - запускает рабочий стол XFCE4

#### 2.7 Настройка окружения ROS

```dockerfile
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc \
    && echo "alias cb='cd ~/ros2_ws && colcon build'" >> ~/.bashrc \
    && echo "alias cs='source ~/ros2_ws/install/setup.bash'" >> ~/.bashrc \
    && echo "alias ws='cd ~/ros2_ws'" >> ~/.bashrc
```

**Что добавляется в .bashrc:**

1. `source /opt/ros/jazzy/setup.bash`
   - Загружает переменные окружения ROS 2
   - Делает доступными команды ros2, rviz2, rqt и т.д.
   - Выполняется автоматически при открытии терминала

2. Полезные алиасы (сокращения команд):
   - `cb` - "colcon build" → переходит в workspace и собирает пакеты
   - `cs` - "colcon source" → загружает собранные пакеты
   - `ws` - "workspace" → быстрый переход в ros2_ws

**Как использовать:**
```bash
# Вместо:
cd ~/ros2_ws && colcon build
source ~/ros2_ws/install/setup.bash

# Можно просто:
cb
cs
```

#### 2.8 Скрипт запуска VNC

```dockerfile
RUN echo '#!/bin/bash' > /home/$USERNAME/start-vnc.sh && \
    echo 'set -e' >> /home/$USERNAME/start-vnc.sh && \
    echo 'echo "Starting VNC server..."' >> /home/$USERNAME/start-vnc.sh && \
    echo 'vncserver :1 -geometry 1920x1080 -depth 24 -localhost no' >> /home/$USERNAME/start-vnc.sh && \
    echo 'echo "VNC server started on :1 (port 5901)"' >> /home/$USERNAME/start-vnc.sh && \
    echo 'echo "Starting noVNC web server..."' >> /home/$USERNAME/start-vnc.sh && \
    echo 'echo "Access desktop at http://localhost:6080/vnc.html"' >> /home/$USERNAME/start-vnc.sh && \
    echo 'exec websockify --web=/usr/share/novnc 6080 localhost:5901' >> /home/$USERNAME/start-vnc.sh && \
    chown $USERNAME:$USERNAME /home/$USERNAME/start-vnc.sh && \
    chmod +x /home/$USERNAME/start-vnc.sh
```

**Содержимое start-vnc.sh:**

```bash
#!/bin/bash
set -e  # Прерывать скрипт при ошибке

echo "Starting VNC server..."
vncserver :1 -geometry 1920x1080 -depth 24 -localhost no

echo "VNC server started on :1 (port 5901)"
echo "Starting noVNC web server..."
echo "Access desktop at http://localhost:6080/vnc.html"

exec websockify --web=/usr/share/novnc 6080 localhost:5901
```

**Объяснение команд:**
- `vncserver :1` - запускает VNC сервер на дисплее :1
- `-geometry 1920x1080` - разрешение экрана
- `-depth 24` - глубина цвета (24 бита = true color)
- `-localhost no` - разрешить подключение не только с localhost
- `websockify` - создает WebSocket прокси между браузером (порт 6080) и VNC (порт 5901)

#### 2.9 Инициализация rosdep и финальные настройки

```dockerfile
RUN rosdep update
```

**Что такое rosdep:**
- Инструмент для управления зависимостями ROS пакетов
- Автоматически устанавливает необходимые системные пакеты
- `rosdep update` обновляет базу данных зависимостей

```dockerfile
USER $USERNAME
WORKDIR /home/$USERNAME/ros2_ws
```

- Убедиться, что мы работаем от пользователя student
- Установить рабочую директорию в ros2_ws

```dockerfile
EXPOSE 5901 6080
```

**Открываемые порты:**
- `5901` - прямое подключение VNC (например, через VNC Viewer)
- `6080` - веб-доступ через noVNC (браузер)

```dockerfile
CMD ["/bin/bash", "-c", "/home/student/start-vnc.sh"]
```

**Команда по умолчанию:**
- Запускается при `docker run`
- Выполняет скрипт start-vnc.sh
- Запускает VNC сервер и noVNC

#### 2.10 Обсуждение: почему такая конфигурация?

**Вопросы для класса:**

1. **Почему мы используем VNC вместо прямого X11?**
   - VNC работает на всех ОС (Mac, Windows, Linux)
   - Не требует настройки X11 forwarding
   - Браузерный доступ - самый простой

2. **Зачем создавать отдельного пользователя, а не работать от root?**
   - Безопасность (root имеет все права)
   - Совместимость с файловой системой хоста
   - Правильная практика разработки

3. **Почему мы монтируем ros2_ws как volume?**
   - Код сохраняется на хосте (не теряется при удалении контейнера)
   - Можно редактировать в VS Code на хосте
   - Можно делать git commit на хосте

4. **Что произойдет, если удалить контейнер?**
   - Потеряются все файлы внутри контейнера
   - НО ros2_ws сохранится (это volume)
   - Можно пересоздать контейнер из того же образа

---

### 3. Настройка VS Code

#### 3.1 Два способа работы с контейнером

**Способ 1: Через VNC в браузере**
- Открыть http://localhost:6080/vnc.html
- Использовать терминал и редакторы внутри VNC
- Преимущества: все в одном месте
- Недостатки: менее удобно, чем родной VS Code

**Способ 2: VS Code с Remote - Containers (рекомендуется)**
- VS Code на хосте подключается к контейнеру
- Можно редактировать файлы, запускать терминалы
- Полный функционал VS Code
- Лучшая производительность

#### 3.2 Установка расширений VS Code

**Необходимые расширения:**
1. **Remote - Containers** (обязательно)
2. **Python** (Microsoft)
3. **ROS** (Microsoft)
4. **C/C++** (Microsoft)

**Установка через терминал:**
```bash
code --install-extension ms-vscode-remote.remote-containers
code --install-extension ms-python.python
code --install-extension ms-iot.vscode-ros
code --install-extension ms-vscode.cpptools
```

**Или через UI:**
- Открыть VS Code
- Extensions (Ctrl+Shift+X)
- Найти и установить каждое расширение

#### 3.3 Подключение к контейнеру

**Метод 1: Attach to Running Container**
1. Нажать F1 (или Ctrl+Shift+P)
2. Ввести "Remote-Containers: Attach to Running Container"
3. Выбрать контейнер `ros2_dev`
4. Откроется новое окно VS Code внутри контейнера
5. File → Open Folder → выбрать `/home/student/ros2_ws`

**Метод 2: Открыть папку с devcontainer.json**
1. Открыть VS Code на хосте
2. File → Open Folder → выбрать `~/robotics_course`
3. VS Code обнаружит Dockerfile.vnc
4. Предложит "Reopen in Container"

#### 3.4 Проверка настройки

**Открыть терминал в VS Code:**
- Terminal → New Terminal (или Ctrl+`)
- Должен быть внутри контейнера (видно `student@контейнер_id`)

**Проверить команды:**
```bash
# Проверка ROS 2
ros2 --version
# Должно показать: ros2 cli version: jazzy

# Проверка Python
python3 --version

# Проверка colcon
colcon version-check

# Проверка workspace
pwd
# Должно быть: /home/student/ros2_ws
```

---

### 4. Создание первого ROS 2 пакета

#### 4.1 Понятие пакета в ROS 2

**Что такое пакет:**
- Минимальная единица организации кода в ROS 2
- Содержит узлы, библиотеки, конфигурационные файлы
- Может зависеть от других пакетов
- Устанавливается и распространяется как единое целое

**Типы пакетов:**
- `ament_python` - Python пакеты (мы будем использовать)
- `ament_cmake` - C++ пакеты (более сложные)

#### 4.2 Создание пакета

**В терминале VS Code или VNC:**

```bash
# Убедимся, что мы в src
cd ~/ros2_ws/src

# Создаем пакет с именем my_robot_controller
ros2 pkg create --build-type ament_python my_robot_controller \
    --dependencies rclpy

# Проверяем структуру
ls -la my_robot_controller/
```

**Объяснение команды:**
- `ros2 pkg create` - команда создания пакета
- `--build-type ament_python` - тип пакета (Python)
- `my_robot_controller` - имя пакета
- `--dependencies rclpy` - зависимость от rclpy (ROS 2 библиотека для Python)

**Созданная структура:**
```
my_robot_controller/
├── my_robot_controller/      # Директория с Python кодом
│   └── __init__.py           # Делает директорию Python пакетом
├── package.xml               # Метаданные пакета
├── resource/                 # Ресурсы пакета
│   └── my_robot_controller
├── setup.cfg                 # Конфигурация установки
├── setup.py                  # Скрипт установки Python
└── test/                     # Тесты
    ├── test_copyright.py
    ├── test_flake8.py
    └── test_pep257.py
```

#### 4.3 Изучение package.xml

**Открыть файл в VS Code:**
```bash
code package.xml
```

**Содержимое:**
```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>my_robot_controller</name>
  <version>0.0.0</version>
  <description>My first ROS 2 package</description>
  <maintainer email="student@todo.todo">student</maintainer>
  <license>TODO: License declaration</license>

  <depend>rclpy</depend>

  <test_depend>ament_copyright</test_depend>
  <test_depend>ament_flake8</test_depend>
  <test_depend>ament_pep257</test_depend>
  <test_depend>python3-pytest</test_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

**Разбор элементов:**

1. **Метаданные:**
   - `<name>` - имя пакета
   - `<version>` - версия (используется семантическое версионирование)
   - `<description>` - описание пакета
   - `<maintainer>` - кто поддерживает пакет
   - `<license>` - лицензия (Apache-2.0, MIT, BSD и т.д.)

2. **Зависимости:**
   - `<depend>rclpy</depend>` - зависимость от rclpy во время сборки и выполнения
   - Другие типы: `<build_depend>`, `<exec_depend>`, `<test_depend>`

3. **Тестовые зависимости:**
   - `ament_copyright` - проверка копирайтов
   - `ament_flake8` - проверка стиля кода (PEP 8)
   - `ament_pep257` - проверка docstrings
   - `python3-pytest` - фреймворк для тестирования

4. **Экспорт:**
   - `<build_type>ament_python</build_type>` - тип сборки

**Задание:** Исправьте email и license в вашем package.xml

#### 4.4 Изучение setup.py

**Открыть файл:**
```bash
code setup.py
```

**Содержимое:**
```python
from setuptools import setup

package_name = 'my_robot_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='student',
    maintainer_email='student@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
```

**Важные части:**

1. **Основная информация:**
   - `name` - имя пакета
   - `version` - версия
   - `packages` - список Python пакетов для установки

2. **data_files:**
   - Файлы, которые копируются при установке
   - `resource/` - индекс пакетов
   - `package.xml` - метаданные

3. **entry_points:**
   - `console_scripts` - исполняемые файлы
   - Сюда мы будем добавлять наши узлы

---

### 5. Система сборки Colcon

#### 5.1 Что такое Colcon

**Colcon (Collective Construction):**
- Система сборки для ROS 2 (замена catkin из ROS 1)
- Собирает все пакеты в workspace
- Управляет зависимостями между пакетами
- Работает с Python, C++, CMake пакетами

**Основные команды:**
```bash
colcon build           # Собрать все пакеты
colcon test            # Запустить тесты
colcon list            # Показать все пакеты
```

#### 5.2 Первая сборка

```bash
# Переходим в корень workspace
cd ~/ros2_ws

# Собираем все пакеты
colcon build

# Или используем алиас
cb
```

**Ожидаемый вывод:**
```
Starting >>> my_robot_controller
Finished <<< my_robot_controller [0.50s]

Summary: 1 package finished [0.65s]
```

**Что создалось:**
```bash
ls -la
```

```
ros2_ws/
├── build/                    # Временные файлы сборки
│   └── my_robot_controller/
├── install/                  # Установленные пакеты
│   ├── local_setup.bash
│   ├── setup.bash           # Главный файл для sourcing
│   ├── my_robot_controller/
│   └── ...
├── log/                     # Логи сборки
│   └── latest_build/
└── src/                     # Исходный код (наш код)
    └── my_robot_controller/
```

#### 5.3 Sourcing установленных пакетов

**Что такое sourcing:**
- Загрузка переменных окружения из собранных пакетов
- Делает ваши узлы видимыми для команды `ros2 run`
- Нужно делать после каждой сборки (в новом терминале)

```bash
# Source установленных пакетов
source install/setup.bash

# Или используем алиас
cs

# Проверяем, что пакет виден
ros2 pkg list | grep my_robot_controller
```

**Автоматический sourcing:**
```bash
# Добавляем в .bashrc (уже должно быть из Dockerfile)
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc

# Перезагружаем .bashrc
source ~/.bashrc
```

#### 5.4 Полезные опции colcon

```bash
# Собрать только один пакет
colcon build --packages-select my_robot_controller

# Собрать с символическими ссылками (для Python - очень удобно!)
colcon build --symlink-install

# Собрать с подробным выводом
colcon build --event-handlers console_direct+

# Собрать параллельно (быстрее на многоядерных процессорах)
colcon build --parallel-workers 4

# Пересобрать все пакеты (очистка + сборка)
colcon build --cmake-clean-cache
```

**Рекомендация для разработки:**
```bash
# Всегда используйте --symlink-install для Python
colcon build --symlink-install
```

**Что делает --symlink-install:**
- Вместо копирования файлов создает символические ссылки
- Изменения в коде сразу видны без пересборки
- Работает только для Python (не для C++)

---

### 6. Создание первого узла ROS 2

#### 6.1 Что такое узел (Node)

**Узел в ROS 2:**
- Программа, выполняющая одну конкретную задачу
- Минимальная единица выполнения в ROS 2
- Узлы общаются друг с другом через топики, сервисы, actions
- Несколько узлов работают одновременно, образуя робототехническую систему

**Примеры узлов:**
- `/camera_node` - получает изображения с камеры
- `/motor_controller` - управляет двигателями
- `/object_detector` - распознает объекты на изображениях
- `/slam_node` - строит карту помещения

#### 6.2 Создание файла узла

```bash
cd ~/ros2_ws/src/my_robot_controller/my_robot_controller

# Создаем файл узла
touch my_first_node.py

# Открываем в VS Code
code my_first_node.py
```

**Содержимое my_first_node.py:**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node


class MyFirstNode(Node):
    """
    Простой узел ROS 2, который выводит сообщения каждую секунду.
    """
    
    def __init__(self):
        # Вызываем конструктор родительского класса
        # Передаем имя узла: 'my_first_node'
        super().__init__('my_first_node')
        
        # Выводим приветственное сообщение
        self.get_logger().info('Hello from ROS 2!')
        
        # Счетчик для отслеживания количества вызовов
        self.counter = 0
        
        # Создаем таймер: каждую 1.0 секунду вызывать timer_callback
        self.create_timer(1.0, self.timer_callback)
    
    def timer_callback(self):
        """
        Эта функция вызывается таймером каждую секунду.
        """
        self.counter += 1
        self.get_logger().info(f'Timer callback {self.counter}')


def main(args=None):
    """
    Точка входа в программу.
    """
    # Инициализация ROS 2
    rclpy.init(args=args)
    
    # Создание узла
    node = MyFirstNode()
    
    # Запуск узла (бесконечный цикл обработки событий)
    rclpy.spin(node)
    
    # Очистка при завершении
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

**Построчное объяснение:**

```python
#!/usr/bin/env python3
```
- **Shebang** - указывает, что файл нужно выполнять через Python 3
- Позволяет запускать файл напрямую: `./my_first_node.py`

```python
import rclpy
from rclpy.node import Node
```
- `rclpy` - библиотека ROS 2 для Python
- `Node` - базовый класс для всех узлов

```python
class MyFirstNode(Node):
```
- Создаем класс нашего узла
- Наследуемся от `Node` - получаем все возможности ROS 2 узла

```python
def __init__(self):
    super().__init__('my_first_node')
```
- Конструктор класса
- `super().__init__('my_first_node')` - вызываем конструктор Node
- `'my_first_node'` - имя узла (будет видно в `ros2 node list`)

```python
self.get_logger().info('Hello from ROS 2!')
```
- `get_logger()` - получаем логгер узла
- `info()` - выводим информационное сообщение
- Уровни логирования: DEBUG, INFO, WARN, ERROR, FATAL

```python
self.counter = 0
```
- Переменная-член класса
- Используется для подсчета вызовов таймера

```python
self.create_timer(1.0, self.timer_callback)
```
- Создаем таймер
- `1.0` - период в секундах (1 секунда)
- `self.timer_callback` - функция, которая будет вызываться

```python
def timer_callback(self):
    self.counter += 1
    self.get_logger().info(f'Timer callback {self.counter}')
```
- Функция обратного вызова (callback)
- Вызывается каждую секунду
- Увеличивает счетчик и выводит сообщение

```python
def main(args=None):
    rclpy.init(args=args)
```
- Точка входа в программу
- `rclpy.init()` - инициализирует ROS 2

```python
node = MyFirstNode()
```
- Создаем экземпляр нашего узла
- Вызывается `__init__`

```python
rclpy.spin(node)
```
- Запускает бесконечный цикл обработки событий
- Обрабатывает таймеры, сообщения, сервисы
- Программа "крутится" здесь до Ctrl+C

```python
rclpy.shutdown()
```
- Очистка ресурсов ROS 2
- Вызывается после выхода из spin (Ctrl+C)

#### 6.3 Регистрация узла в setup.py

Нужно добавить entry point, чтобы узел можно было запустить через `ros2 run`.

**Открыть setup.py:**
```bash
code ~/ros2_ws/src/my_robot_controller/setup.py
```

**Найти секцию entry_points и добавить:**
```python
entry_points={
    'console_scripts': [
        'my_first_node = my_robot_controller.my_first_node:main',
    ],
},
```

**Объяснение:**
- `my_first_node` - имя исполняемого файла (можно запустить через `ros2 run`)
- `my_robot_controller.my_first_node` - путь к модулю Python
- `main` - функция, которая будет вызвана

---

### 7. Сборка и запуск узла

#### 7.1 Сборка пакета

```bash
# Переходим в workspace
cd ~/ros2_ws

# Собираем с symlink (изменения без пересборки)
colcon build --packages-select my_robot_controller --symlink-install

# Или используем алиас
cb --packages-select my_robot_controller --symlink-install

# Source
source install/setup.bash
# Или: cs
```

**Если сборка прошла успешно:**
```
Starting >>> my_robot_controller
Finished <<< my_robot_controller [0.5s]

Summary: 1 package finished [0.6s]
```

#### 7.2 Запуск узла

```bash
# Запускаем узел
ros2 run my_robot_controller my_first_node
```

**Ожидаемый вывод:**
```
[INFO] [1699999999.999999999] [my_first_node]: Hello from ROS 2!
[INFO] [1700000000.999999999] [my_first_node]: Timer callback 1
[INFO] [1700000001.999999999] [my_first_node]: Timer callback 2
[INFO] [1700000002.999999999] [my_first_node]: Timer callback 3
...
```

**Остановка узла:**
- Нажать Ctrl+C

#### 7.3 Исследование узла

**Открыть второй терминал в VS Code:**
- Terminal → Split Terminal
- Или Terminal → New Terminal

**В новом терминале:**

```bash
# Список всех запущенных узлов
ros2 node list

# Должен показать:
# /my_first_node

# Подробная информация об узле
ros2 node info /my_first_node

# Вывод:
# /my_first_node
#   Subscribers:
#   Publishers:
#   Service Servers:
#   Service Clients:
#   Action Servers:
#   Action Clients:
```

**Граф узлов (если есть GUI):**
```bash
# Запускаем rqt_graph для визуализации
ros2 run rqt_graph rqt_graph
```

- Откроется графическое окно
- Должен быть виден узел `/my_first_node`
- Пока нет связей (узел ни с кем не общается)

---

### 8. Коммит изменений в Git

#### 8.1 Инициализация репозитория

```bash
cd ~/ros2_ws

# Проверяем статус Git
git status

# Если репозиторий еще не инициализирован:
git init

# Настраиваем пользователя (если еще не делали)
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

#### 8.2 Создание .gitignore

**Создаем файл .gitignore:**
```bash
cat > .gitignore << 'EOF'
# ROS 2
build/
install/
log/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
EOF
```

#### 8.3 Коммит

```bash
# Добавляем все файлы
git add .

# Проверяем, что будет закоммичено
git status

# Делаем коммит
git commit -m "Add first ROS 2 node: my_first_node"

# Просмотр истории
git log --oneline
```

#### 8.4 Push в GitLab

```bash
# Добавляем remote (замените на свой URL)
git remote add origin https://gitlab.com/username/robotics_course.git

# Пушим в main ветку
git push -u origin main

# Или создаем новую ветку
git checkout -b lesson-2
git push -u origin lesson-2
```

---

## Домашнее задание

### Задание 1: Модификация узла (обязательно)

**Цель:** Научиться изменять параметры узла

1. Измените частоту таймера с 1.0 на 0.5 секунды
2. Добавьте вывод текущего времени в лог
3. Пересоберите пакет (не забудьте `--symlink-install`)
4. Запустите и убедитесь, что изменения работают

**Подсказка для времени:**
```python
import time

current_time = time.time()
self.get_logger().info(f'Timer callback {self.counter}, time: {current_time}')
```

### Задание 2: Создание второго узла (обязательно)

**Цель:** Создать еще один узел с другими параметрами

1. Создайте файл `my_second_node.py` в том же пакете
2. Узел должен выводить "Node 2 is alive!" каждые 2 секунды
3. Добавьте entry point в `setup.py`:
   ```python
   'my_second_node = my_robot_controller.my_second_node:main',
   ```
4. Соберите пакет
5. Запустите оба узла одновременно (в разных терминалах)
6. Проверьте список узлов: `ros2 node list`

### Задание 3: Исследование Turtlesim (дополнительно)

**Цель:** Познакомиться с существующими ROS 2 пакетами

1. Запустите turtlesim:
   ```bash
   ros2 run turtlesim turtlesim_node
   ```

2. В другом терминале запустите управление:
   ```bash
   ros2 run turtlesim turtle_teleop_key
   ```

3. Исследуйте систему:
   ```bash
   # Список узлов
   ros2 node list
   
   # Список топиков
   ros2 topic list
   
   # Просмотр сообщений позиции черепашки
   ros2 topic echo /turtle1/pose
   
   # Информация о топике
   ros2 topic info /turtle1/cmd_vel
   ```

4. Запишите в отчет:
   - Сколько узлов запущено?
   - Какие топики есть в системе?
   - Какой тип сообщений использует `/turtle1/cmd_vel`?

### Задание 4: Эксперименты с узлом (дополнительно)

**Цель:** Понять структуру узла глубже

Модифицируйте `my_first_node.py`:

1. Добавьте второй таймер с частотой 0.2 секунды
2. Второй таймер должен выводить "Fast timer!"
3. Должны быть два отдельных callback'а
4. Оба таймера работают одновременно

**Подсказка:**
```python
self.create_timer(1.0, self.slow_callback)
self.create_timer(0.2, self.fast_callback)
```

### Задание 5: Git (обязательно)

1. Закоммитьте все изменения из заданий 1-4
2. Напишите осмысленные commit messages:
   ```bash
   git add .
   git commit -m "Change timer frequency to 0.5 seconds"
   git commit -m "Add second node"
   ```
3. Запушьте в GitLab

### Задание 6: Подготовка к следующему занятию

**Что изучить:**

1. **ROS 2 Topics:**
   - https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html

2. **Publisher/Subscriber:**
   - https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html

3. **ROS 2 Interfaces:**
   - https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html

**Вопросы для самопроверки:**
- Что такое топик?
- В чем разница между Publisher и Subscriber?
- Что такое тип сообщения (message type)?
- Зачем нужны топики в робототехнике?

---

## Материалы для занятия

### Оборудование
- Ноутбуки учащихся с запущенным Docker контейнером
- Проектор для демонстрации
- Доступ к интернету (для GitLab)

### Файлы
- Dockerfile.vnc (уже у студентов)
- my_first_node.py (пример)
- .gitignore (шаблон)

---

## Справочные материалы

### Полезные команды ROS 2

```bash
# Управление пакетами
ros2 pkg list                              # Список всех пакетов
ros2 pkg create --build-type ament_python <name>  # Создать пакет
ros2 pkg executables <package>             # Исполняемые файлы пакета

# Управление узлами
ros2 run <package> <executable>            # Запустить узел
ros2 node list                             # Список запущенных узлов
ros2 node info <node_name>                 # Информация об узле

# Управление топиками (следующее занятие)
ros2 topic list                            # Список топиков
ros2 topic echo <topic>                    # Просмотр сообщений
ros2 topic info <topic>                    # Информация о топике
ros2 topic pub <topic> <msg_type> '<data>' # Публикация в топик

# Инструменты
rqt_graph                                  # Граф узлов
ros2 doctor                                # Диагностика проблем
```

### Полезные команды Colcon

```bash
# Сборка
colcon build                               # Собрать все
colcon build --packages-select <pkg>      # Собрать один пакет
colcon build --symlink-install            # Symlinks для Python
colcon build --parallel-workers 4         # Параллельная сборка

# Информация
colcon list                                # Список пакетов
colcon info                                # Информация о workspace

# Тесты
colcon test                                # Запустить тесты
colcon test-result --all                   # Результаты тестов
```

### Полезные команды Git

```bash
# Базовые
git init                                   # Инициализация
git status                                 # Статус
git add .                                  # Добавить все
git commit -m "message"                    # Коммит
git push origin main                       # Отправить на сервер

# Просмотр
git log                                    # История
git log --oneline --graph                  # Краткая история
git diff                                   # Изменения

# Ветки
git branch                                 # Список веток
git checkout -b <name>                     # Создать ветку
git merge <branch>                         # Слить ветку
```

### Структура ROS 2 workspace

```
ros2_ws/
├── src/                      # Исходный код (мы пишем здесь)
│   └── my_robot_controller/
│       ├── my_robot_controller/
│       │   ├── __init__.py
│       │   ├── my_first_node.py
│       │   └── my_second_node.py
│       ├── package.xml
│       └── setup.py
├── build/                    # Временные файлы (не трогаем)
├── install/                  # Собранные пакеты (не трогаем)
│   └── setup.bash           # Source этот файл!
└── log/                     # Логи сборки (не трогаем)
```

---

## Заметки для преподавателя

### Типичные проблемы и решения

**1. Контейнер не запускается**
- Проверить, что Docker запущен: `docker ps`
- Проверить порты: `netstat -an | grep 6080`
- Пересоздать контейнер: `docker rm ros2_dev` и запустить снова

**2. VNC показывает черный экран**
- Подождать 30 секунд после запуска
- Проверить логи: `docker logs ros2_dev`
- Перезапустить контейнер: `docker restart ros2_dev`

**3. VS Code не подключается**
- Проверить, что установлено расширение Remote - Containers
- Проверить, что контейнер запущен
- Попробовать переустановить расширение

**4. colcon build завершается с ошибкой**
- Проверить синтаксис Python: `python3 -m py_compile my_first_node.py`
- Проверить setup.py на ошибки
- Проверить права на файлы: `chmod +x my_first_node.py`

**5. ros2 run не находит узел**
- Проверить, что сделали `source install/setup.bash`
- Проверить entry point в setup.py
- Пересобрать с `colcon build --packages-select <pkg>`

**6. Узел не запускается**
- Проверить shebang: `#!/usr/bin/env python3`
- Проверить права: `chmod +x my_first_node.py`
- Проверить импорты: `import rclpy`
- Запустить напрямую: `python3 my_first_node.py` (покажет ошибки)

### Управление временем

**Если опережаем:**
- Показать rqt подробнее (rqt_console, rqt_plot)
- Создать третий узел вместе с классом
- Начать тему про топики (следующее занятие)
- Показать параметры узлов

**Если отстаем:**
- Домашнее задание: самостоятельно разобраться с Git
- Пропустить детальный разбор каждой строки Dockerfile
- Показать готовый код узла без пошагового написания
- Упростить домашнее задание

### Дифференциация по уровням

**Сильные студенты:**
- Дать дополнительное задание: узел с параметрами (`self.declare_parameter`)
- Попросить помочь другим с настройкой
- Предложить изучить C++ узлы
- Создать узел с несколькими таймерами разной частоты

**Слабые студенты:**
- Дать готовые шаблоны файлов
- Работать в паре с сильным студентом
- Больше времени на объяснение базовых концепций
- Упрощенное домашнее задание (только задание 1)

### Работа в командах

**Организация:**
- Один ноутбук на команду для совместной работы
- Ротация ролей: один пишет код, другой комментирует
- Общий Git репозиторий для команды

**Распределение ролей:**
- **Driver** - пишет код
- **Navigator** - проверяет, подсказывает
- **Researcher** - ищет информацию в документации
- Роли меняются каждые 15 минут

### Контроль понимания

**Вопросы для проверки:**
1. Объясните, зачем в Dockerfile нужен VNC?
2. Что такое workspace в ROS 2?
3. Зачем нужен `source install/setup.bash`?
4. Что делает `colcon build --symlink-install`?
5. Что такое узел (Node) в ROS 2?
6. Зачем в setup.py нужен entry_points?

**Практическая проверка:**
- Все запустили контейнер
- Все подключились через VS Code или VNC
- Все создали и собрали пакет
- Все запустили свой узел
- Все сделали коммит в Git

**Критерии успеха занятия:**
- 80%+ студентов запустили свой узел
- 70%+ студентов сделали коммит в Git
- 60%+ студентов понимают структуру узла
- 100% студентов имеют доступ к контейнеру