@echo off
REM Prerequisites installer for NVIDIA Isaac ROS (Docker mode) on Windows + WSL2.
REM Requirements: Admin rights, NVIDIA GPU driver, Docker Desktop (WSL backend), Ubuntu WSL distro.

setlocal EnableDelayedExpansion

echo === NVIDIA Isaac ROS prerequisites (Docker) ===

REM ---- Checks ----
where nvidia-smi >nul 2>&1
if errorlevel 1 (
  echo [ERROR] nvidia-smi не найден. Установите/обновите драйвер NVIDIA и перезагрузите систему.
  exit /b 1
)

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker Desktop не установлен или не в PATH. Установите Docker Desktop, включите WSL2 backend и GPU support.
  exit /b 1
)

wsl.exe --status >nul 2>&1
if errorlevel 1 (
  echo [ERROR] WSL2 не включен или нет дистрибутива. Выполните: wsl --install --distribution Ubuntu
  exit /b 1
)

REM ---- Run setup inside default WSL distro ----
echo [INFO] Настраиваем Isaac ROS CLI в WSL (Ubuntu)
wsl -e sh -c "\
set -euo pipefail; \
if [ \"$(id -u)\" -eq 0 ]; then SUDO=; else SUDO=sudo; fi; \
if [ ! -f /etc/os-release ]; then echo 'Unsupported distro'; exit 1; fi; \
. /etc/os-release; \
if [ \"$VERSION_CODENAME\" != \"jammy\" ] && [ \"$VERSION_CODENAME\" != \"noble\" ]; then echo 'Warning: tested on Ubuntu 22.04/24.04 only'; fi; \
$SUDO apt-get update -y; \
$SUDO apt-get install -y curl gnupg2 ca-certificates lsb-release; \
KEY=/usr/share/keyrings/nvidia-isaac-ros.gpg; \
curl -fsSL https://isaac.download.nvidia.com/isaac-ros/repos.key | $SUDO gpg --dearmor -o $KEY; \
LIST=/etc/apt/sources.list.d/nvidia-isaac-ros.list; \
echo \"deb [signed-by=$KEY] https://isaac.download.nvidia.com/isaac-ros/release-4 $VERSION_CODENAME main\" | $SUDO tee $LIST >/dev/null; \
$SUDO apt-get update -y; \
$SUDO apt-get install -y isaac-ros-cli python3-termcolor; \
$SUDO isaac-ros init docker; \
echo '[OK] WSL сторона настроена.' \
" || (
  echo [ERROR] Не удалось выполнить настройку в WSL.
  exit /b 1
)

REM ---- Optional GPU smoke test ----
echo [INFO] Запускаем тестовый контейнер nvidia/cuda (может занять время для первого pull)
docker run --rm --gpus all --pull=missing nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
if errorlevel 1 (
  echo [WARN] Тестовый контейнер завершился с ошибкой. Проверьте вывод выше.
  exit /b 1
)

echo [DONE] Пререквизиты для NVIDIA Isaac ROS (Docker) установлены. Можно запускать isaac-ros CLI внутри WSL.
endlocal