host='localhost' # Передать как параметр

cd ./../IsaacSim/tools/docker
docker run --name isaac-sim --rm -it --gpus all --network=host \
  -e ACCEPT_EULA=Y \
  -e ISAACSIM_HOST=$host \
  isaac-sim-docker:latest
