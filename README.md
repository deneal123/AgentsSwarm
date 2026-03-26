нужно 100+ гигабайт для полного набора расширений

./tools/docker/prep_docker_build.sh --build --x86_64
/tools/docker/build_docker.sh --x86_64

docker compose -p isim -f tools/docker/docker-compose.yml up --build -d

нужно положить .env файл в директорию рядом с docker-compose.yml

Variable	Default	Description
ISAAC_SIM_IMAGE	isaac-sim-docker:latest	Docker image to run. Set to a prebuilt NGC image (e.g. nvcr.io/nvidia/isaac-sim:6.0.0-dev2) to skip local build steps.
ISAACSIM_HOST	127.0.0.1	Host IP for WebRTC streaming (used by both services). See Cloud Deployment for cloud VMs.
ISAACSIM_SIGNAL_PORT	49100	WebRTC signaling port (TCP)
ISAACSIM_STREAM_PORT	47998	WebRTC media port (UDP)
WEB_VIEWER_PORT	8210	Host port for the web viewer
GPU_DEVICE	all	GPU index to pin the Isaac Sim container to (e.g. 0, 1)
ISAAC_SIM_DATA	~/docker/isaac-sim	Host path for persistent cache, config, logs, and data. Use a full absolute path in .env files (~ is not expanded by Docker Compose).

docker compose -p isim logs              # combined logs from both containers
docker compose -p isim logs web-viewer   # web viewer only (shows the URL)
docker compose -p isim logs isaac-sim    # Isaac Sim only (look for "app ready")
docker compose -p isim logs -f           # follow live logs (Ctrl+C to stop)