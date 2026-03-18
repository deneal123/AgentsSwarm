Isaac Sim Requirements
Hint

By installing Isaac Sim, you can run the Isaac Sim Compatibility Checker lightweight app to check if your machine meets the system requirements and compatibility.

System Requirements
Element

Minimum Spec

Good

Ideal

OS

Ubuntu 22.04/24.04
Windows 10/11
Ubuntu 22.04/24.04
Windows 10/11
Ubuntu 22.04/24.04
Windows 10/11
CPU

Intel Core i7 (7th Generation)
AMD Ryzen 5
Intel Core i7 (9th Generation)
AMD Ryzen 7
Intel Core i9, X-series or higher
AMD Ryzen 9, Threadripper or higher
Cores

4
8
16
RAM [1]

32GB
64GB
64GB
Storage

50GB SSD
500GB SSD
1TB NVMe SSD
GPU

GeForce RTX 4080
GeForce RTX 5080
RTX PRO 6000 Blackwell
VRAM [1]

16GB [2]
16GB
48GB
Driver [3]

Linux: 580.65.06
Windows: 580.88
Linux: 580.65.06
Windows: 580.88
Linux: 580.65.06
Windows: 580.88
[1](1,2)
More RAM and VRAM is recommended for advanced usage of Isaac Sim. Isaac Lab usage will require additional RAM and VRAM for training.

[2]
GPUs with less than 16GB VRAM may be insufficient to run a complex scene rendering more than 16MP per frame. Consider upgrading to a higher spec if that is your use case.

[3]
Isaac Sim was tested on these driver versions. See Technical Requirements for recommended driver versions.

Note

The Isaac Sim container is only supported on Linux.

An Internet connection is required to access the Isaac Sim assets online and to run some extensions.

GPUs without RT Cores (A100, H100) are not supported.

Due to VRAM constraints, some tutorials and benchmarks may not run on GPU below the minimum specifications. Workflows leveraging a large number of sensors are particularly affected.

See Linux Troubleshooting to resolve driver installation issues on Linux.

We recommend installing the Latest Production Branch Version drivers from the Unix Driver Archive using the .run installer on Linux if you are on a new GPU or experiencing issues with the current drivers.

Windows 10 support ends on October 14, 2025. After this date, Microsoft will no longer provide free security, feature, or technical updates for Windows 10. As a result, we will be dropping support for Windows 10 in future releases of Isaac Sim to ensure the security and functionality of our software.

Container Installation
The container installation of Isaac Sim is recommended for deployment on remote headless servers or the Cloud using a Docker container running Linux.

See also

Differences Between Workstation And Docker

Container Setup
Ensure your system meets the System Requirements for running NVIDIA Isaac Sim.

Install Docker:

Docker installation using the convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

Post-install steps for Docker
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker

Verify Docker
docker run hello-world
See also

Install Docker Engine on Ubuntu

Post-installation steps for Linux

Install the NVIDIA Container Toolkit:

Configure the repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list \
    && \
    sudo apt-get update

Install the NVIDIA Container Toolkit packages
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

Configure the container runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

Verify NVIDIA Container Toolkit
docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
Note

Install the latest version of NVIDIA Container Toolkit to get security fixes.

Container Deployment
This section describes how to run the NVIDIA Isaac Sim container in headless mode with livestreaming.

Steps:

Setup and install the container prerequisites. See Container Setup above.

Run the following command to confirm your GPU driver version:

nvidia-smi
Pull the Isaac Sim Container:

docker pull nvcr.io/nvidia/isaac-sim:5.1.0
Create the cached volume mounts on host:

mkdir -p ~/docker/isaac-sim/cache/main/ov
mkdir -p ~/docker/isaac-sim/cache/main/warp
mkdir -p ~/docker/isaac-sim/cache/computecache
mkdir -p ~/docker/isaac-sim/config
mkdir -p ~/docker/isaac-sim/data/documents
mkdir -p ~/docker/isaac-sim/data/Kit
mkdir -p ~/docker/isaac-sim/logs
mkdir -p ~/docker/isaac-sim/pkg
sudo chown -R 1234:1234 ~/docker/isaac-sim
Run the Isaac Sim container with an interactive Bash session:

docker run --name isaac-sim --entrypoint bash -it --gpus all -e "ACCEPT_EULA=Y" --rm --network=host \
    -e "PRIVACY_CONSENT=Y" \
    -v ~/docker/isaac-sim/cache/main:/isaac-sim/.cache:rw \
    -v ~/docker/isaac-sim/cache/computecache:/isaac-sim/.nv/ComputeCache:rw \
    -v ~/docker/isaac-sim/logs:/isaac-sim/.nvidia-omniverse/logs:rw \
    -v ~/docker/isaac-sim/config:/isaac-sim/.nvidia-omniverse/config:rw \
    -v ~/docker/isaac-sim/data:/isaac-sim/.local/share/ov/data:rw \
    -v ~/docker/isaac-sim/pkg:/isaac-sim/.local/share/ov/pkg:rw \
    -u 1234:1234 \
    nvcr.io/nvidia/isaac-sim:5.1.0
Note

The Isaac Sim container now runs as a rootless user.

The Isaac Sim container now supports multi-arch. The same tag can be run on Linux x86_64 and aarch64 systems.

By using the -e "ACCEPT_EULA=Y" flag, you accept the license agreement of the image found at NVIDIA Omniverse License Agreement.

By using the -e "PRIVACY_CONSENT=Y" flag, you opt-in to the data collection agreement found at Data Collection & Usage. You may opt-out by not setting this flag.

The -e "PRIVACY_USERID=<email>" flag can optionally be set for tagging the session logs.

Add the --runtime=nvidia flag if there are issues detecting the GPU in the container.

For enterprise users, see Enterprise Nucleus Server.

The Isaac Sim container uses assets in the Cloud if no Nucleus server is available.

When using a separate Nucleus server:

See Problem Connecting to Docker Container to expose all ports of the container and connect to an external Nucleus server.

See Setting the Default Nucleus Server to set the default Nucleus server.

See Setting the Default Username and Password for Connecting to the Nucleus Server to set the default credentials for any Nucleus server.

Check if your system is compatible with Isaac Sim:

./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
Note

To run the Compatibility Checker separately:

docker run --entrypoint bash -it --gpus all --rm --network=host \
    nvcr.io/nvidia/isaac-sim:5.1.0 ./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
You should see the text “System checking result: PASSED” if your system is compaitble.

Start Isaac Sim with native livestream mode:

./runheadless.sh -v
Warning

Livestreaming is not supported on aarch64 systems like DGX Spark for Isaac Sim 5.1.0.

See Container Deployment with GUI.

Note

Before running a livestream client, you must have the Isaac Sim app loaded and ready.
It may take a few minutes for Isaac Sim to completely load.

The -v flag is used to show additional logs while the shader cache is being warmed up.

To confirm this, look out for this line in the console or the logs:

Isaac Sim Full Streaming App is loaded.
The first time loading Isaac Sim, it takes a while for the shaders to be cached. Subsequent runs of Isaac Sim are quicker because the shaders are cached and the cache is mounted when the container runs.

See Save Isaac Sim Configs on Local Disk to make Isaac Sim configs and cache persistent when using containers.

Download and install the Isaac Sim WebRTC Streaming Client from the Latest Release section.

Run the Isaac Sim WebRTC Streaming Client.

Enter the IP address of the machine or instance running the Isaac Sim container and click on the Connect button to begin live streaming.

Proceed to Quick Tutorials to begin your first tutorial.

Note

Some tutorials that use the Content Browser may not work when using the Isaac Sim container with no Nucleus connected.

It is recommended to use the Workstation Isaac Sim from the Omniverse Launcher to run all tutorials.

The Isaac Sim container supports running our Python apps and standalone examples in headless mode only.

The latest NVIDIA drivers may not be fully supported for some features like livestreaming. See Technical Requirements for recommended drivers.

See also Isaac Sim Dockerfiles to build your own custom Isaac Sim container.

You can debug Python Scripts Running in Docker.

Container Deployment with GUI
This section describes how to run the NVIDIA Isaac Sim container with GUI.

Steps:

Setup and install the container prerequisites. See Container Setup above.

Run the following command to confirm your GPU driver version:

nvidia-smi
Pull the Isaac Sim Container:

docker pull nvcr.io/nvidia/isaac-sim:5.1.0
Create the cached volume mounts on host:

mkdir -p ~/docker/isaac-sim/cache/main/ov
mkdir -p ~/docker/isaac-sim/cache/main/warp
mkdir -p ~/docker/isaac-sim/cache/computecache
mkdir -p ~/docker/isaac-sim/config
mkdir -p ~/docker/isaac-sim/data/documents
mkdir -p ~/docker/isaac-sim/data/Kit
mkdir -p ~/docker/isaac-sim/logs
mkdir -p ~/docker/isaac-sim/pkg
sudo chown -R 1234:1234 ~/docker/isaac-sim
Run the Isaac Sim container with an interactive Bash session:

xhost +local:
docker run --name isaac-sim --entrypoint bash -it --gpus all -e "ACCEPT_EULA=Y" --rm --network=host \
    -e "PRIVACY_CONSENT=Y" \
    -v $HOME/.Xauthority:/isaac-sim/.Xauthority \
    -e DISPLAY \
    -v ~/docker/isaac-sim/cache/main:/isaac-sim/.cache:rw \
    -v ~/docker/isaac-sim/cache/computecache:/isaac-sim/.nv/ComputeCache:rw \
    -v ~/docker/isaac-sim/logs:/isaac-sim/.nvidia-omniverse/logs:rw \
    -v ~/docker/isaac-sim/config:/isaac-sim/.nvidia-omniverse/config:rw \
    -v ~/docker/isaac-sim/data:/isaac-sim/.local/share/ov/data:rw \
    -v ~/docker/isaac-sim/pkg:/isaac-sim/.local/share/ov/pkg:rw \
    -u 1234:1234 \
    nvcr.io/nvidia/isaac-sim:5.1.0
Check if your system is compatible with Isaac Sim:

./isaac-sim.compatibility_check.sh
Start Isaac Sim with GUI:

./runapp.sh
Proceed to Quick Tutorials to begin your first tutorial.

Warning

Running Isaac Sim with GUI in the container is generally not recommended.

The application experience may not be as expected. For a full GUI app experience please run Isaac Sim with the Workstation Installation.