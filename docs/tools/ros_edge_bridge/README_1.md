# ROS 2 Jazzy Desktop

Docker окружение для работы с ROS 2 Jazzy с GUI через браузер.

## Быстрый старт

### Сборка и запуск

```bash
# Сборка образа с VNC
docker build -f Dockerfile.vnc -t ros2-jazzy-vnc .

# Запуск контейнера
docker run -d --name ros2-desktop -p 6080:6080 -p 5901:5901 -p 8765:8765 ros2-jazzy-vnc


### Доступ к GUI

Откройте в браузере: **http://localhost:6080/vnc.html**

**Пароль:** `student`

**Copy/Paste:** Работает через noVNC - используйте Ctrl+C/Ctrl+V в браузере

## Тестирование ROS 2

В терминале внутри VNC:

```bash
# Запуск RViz2
rviz2

# Запуск RQT
rqt


# Тест с turtlesim
ros2 run turtlesim turtlesim_node
```

### Использование Foxglove

**Foxglove Bridge** (рекомендуется):

1. В контейнере запустите: `ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765 -p address:=0.0.0.0`
2. Откройте [Foxglove Studio Web](https://studio.foxglove.dev/) в браузере
3. Подключитесь к `ws://localhost:8765`

**Примечание**: Foxglove Studio desktop не установлен (недоступен для ARM64/Apple Silicon)

## Полезные команды

```bash
# Вход в контейнер
docker exec -it ros2-desktop bash

# Логи
docker logs -f ros2-desktop

# Остановка
docker stop ros2-desktop

# Удаление
docker rm ros2-desktop
```

## Алиасы внутри контейнера

- `ws` - переход в workspace (`cd ~/ros2_ws`)
- `cb` - сборка проектов (`colcon build`)
- `cs` - активация окружения (`source install/setup.bash`)

## Монтирование проектов

```bash
docker run -d --name ros2-desktop \
  -p 6080:6080 -p 5901:5901 -p 8765:8765 \
  -v "$PWD/workspace:/home/student/ros2_ws/src" \
  ros2-jazzy-vnc
```

Файлы из `./workspace/` будут доступны в контейнере.

## Альтернатива VNC

Для работы без GUI используйте базовый Dockerfile:

```bash
docker build -t ros2-jazzy-student .
docker run -it ros2-jazzy-student
```

```bash
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update -y
sudo apt-get install ./docker-desktop-amd64.deb
sudo apt install docker.io
sudo systemctl start docker
docker load < ./ros2-jazzy-vnc.tar.gz
```

Презентация
```
https://docs.google.com/presentation/d/1sU_dXnhXtarupLcZ3rEqd6IBBQt5P5tumVFY_dli8FA/edit?slide=id.p3#slide=id.p3
```

LMS
```
https://lms.yandex.ru/courses/1571/groups/52520
```

GITLAB

```
https://gitlab.crja72.ru/pavolotsky/physicalai
```