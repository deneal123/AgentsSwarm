#!/usr/bin/env bash

# Prerequisites installer for NVIDIA Isaac ROS (Docker mode).
# Target: Ubuntu 22.04/24.04 with NVIDIA GPU and sudo rights.

set -euo pipefail

ESC=$(printf '\033')
GREEN="$ESC[32m"; YELLOW="$ESC[33m"; RED="$ESC[31m"; RESET="$ESC[0m"
info(){ printf "%b%s%b\n" "$GREEN" "$1" "$RESET"; }
warn(){ printf "%b%s%b\n" "$YELLOW" "$1" "$RESET"; }
err(){ printf "%b%s%b\n" "$RED" "$1" "$RESET"; }

require_cmd(){ if ! command -v "$1" >/dev/null 2>&1; then err "Команда $1 не найдена"; exit 1; fi; }

OS_CODENAME=$( . /etc/os-release && echo "$VERSION_CODENAME" )
if [[ "$OS_CODENAME" != "jammy" && "$OS_CODENAME" != "noble" ]]; then
  warn "Скрипт протестирован на Ubuntu 22.04 (jammy) и 24.04 (noble). Продолжаем на свой страх и риск."
fi

info "Обновляем индекс пакетов и базовые зависимости"
sudo apt-get update -y
sudo apt-get install -y curl gnupg2 ca-certificates lsb-release software-properties-common

info "Проверяем nvidia-smi (установите/обновите драйвер, если команда не работает)"
if ! command -v nvidia-smi >/dev/null 2>&1; then
  err "nvidia-smi не найден. Установите проприетарный драйвер NVIDIA и перезагрузите систему."
  exit 1
fi

info "Устанавливаем Docker Engine (если не установлен)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $OS_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker "$USER" || true
  warn "Перелогиньтесь, чтобы применились права docker-группы."
fi

info "Устанавливаем NVIDIA Container Toolkit"
distribution=$( . /etc/os-release; echo "$ID$VERSION_ID" )
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit.gpg] https://#' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
sudo apt-get update -y
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

info "Добавляем репозиторий NVIDIA Isaac ROS и ставим isaac-ros-cli"
ISAAC_KEY="/usr/share/keyrings/nvidia-isaac-ros.gpg"
curl -fsSL https://isaac.download.nvidia.com/isaac-ros/repos.key | sudo gpg --dearmor -o "$ISAAC_KEY"
ISAAC_LIST="/etc/apt/sources.list.d/nvidia-isaac-ros.list"
echo "deb [signed-by=$ISAAC_KEY] https://isaac.download.nvidia.com/isaac-ros/release-4 $OS_CODENAME main" | sudo tee "$ISAAC_LIST" >/dev/null
sudo apt-get update -y
sudo apt-get install -y isaac-ros-cli python3-termcolor

info "Инициализируем Isaac ROS CLI в режиме Docker"
sudo isaac-ros init docker

info "Быстрая проверка docker + GPU (может занять 1-2 минуты на первый pull)"
if docker info >/dev/null 2>&1; then
  docker run --rm --gpus all --pull=missing nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi || warn "Тестовый контейнер завершился с ошибкой. Проверьте вывод выше."
else
  warn "Docker недоступен для текущего пользователя. Проверьте группу docker и перезапустите сессию."
fi

info "Готово. Можно использовать isaac-ros CLI и запускать контейнеры."