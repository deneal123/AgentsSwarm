host='localhost' # Передать как параметр

cd ./../IsaacSim/tools/docker
docker run --name isaac-sim --rm -it --gpus all --network=host \
  -e ACCEPT_EULA=Y \
  isaac-sim-docker:latest

# ISAAC_SIM_IMAGE=nvcr.io/nvidia/isaac-sim:6.0.0-dev2 docker compose -p isim -f tools/docker/docker-compose.yml up --build -d