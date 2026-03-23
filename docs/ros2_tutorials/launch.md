ROS 2 Launch
Note

ROS 2 Launch with Isaac Sim is only supported in Linux. The isaacsim package is not supported in WSL2.

Learning Objectives
In this tutorial, we are demonstrating running NVIDIA Isaac Sim from a ROS 2 launch file.

Prerequisite

ROS 2 Launch for Isaac Sim is only supported on Linux.

Completed ROS 2 Navigation for ROS 2 Nav2 with a single robot. So that

ROS 2 and Nav2 are installed.

ROS 2 bridge is enabled.

This tutorial requires the carter_navigation, isaac_ros_navigation_goal, and isaacsim ROS 2 packages that are provided as part of your NVIDIA Isaac Sim download. These ROS 2 packages are located inside the appropriate ros2_ws. They contain the required launch files, navigation parameters, and robot model. Complete ROS 2 Installation (Default), make sure the ROS 2 workspace environment is setup correctly.

Launching Isaac Sim with ROS 2
The isaacsim package contains scripts and ROS 2 launch file to launch Isaac Sim.

The launch file called run_isaacsim.launch.py is included in the launch folder of the isaacsim package.

The launch parameters are defined below:

version: Specify the version of Isaac Sim to use. Isaac Sim will be run from default install root folder for the specified version. Leave empty to use latest version of Isaac Sim. [default_value = “6.0.0”]

install_path: If Isaac Sim is installed in a non-default location, provide a specific path to Isaac Sim installation root folder. (If defined, “version” parameter will be ignored). [default_value = “”]

use_internal_libs: Set to true if you wish to use internal ROS libraries shipped with Isaac Sim. [default_value = “true”]

Note

As of Isaac Sim 6.0 only Python 3.12 is supported. Therefore use_internal_libs (compiled with Python 3.12) are now set to true by default. If your own ROS installation is built with Python 3.12, you can set use_internal_libs to false.

dds_type: Set to “fastdds” or “cyclonedds” to run Isaac Sim with a specific dds type. [default_value = “fastdds”]

gui: Provide the path to a USD file to open it when starting Isaac Sim in standard gui mode. If left empty, Isaac Sim will open an empty stage in standard gui mode. [default_value = “”]

standalone: Provide the path to the Python file to open it and start Isaac Sim in standalone workflow. If left empty, Isaac Sim will open an empty stage in standard Gui mode. [default_value = “”]

play_sim_on_start: If enabled and Isaac Sim will start playing the scene after it is loaded. (Only applicable when in standard gui mode). [default_value = “false”]

ros_distro: Provide ROS version to use. Both Jazzy and Humble is supported. [default_value = “humble”]

ros_installation_path: Comma-separated list of ROS installation paths. If ROS is installed in a non-default location (as in not under /opt/ros/), provide the path to your main setup.bash file for your ROS install. (/path/to/custom/ros/install/setup.bash). Similarly add the path to your local_setup.bash file for your workspace installation. (/path/to/custom_ros_workspace/install/local_setup.bash). [default_value = “”]

headless: Set to “webrtc” to run Isaac Sim in headless mode with WebRTC. If left empty, Isaac Sim will run in the standard gui mode. This parameter can be overridden by “standalone” parameter. [default_value = “”]

custom_args: Add any custom Isaac Sim args that you want to forward to isaac-sim.sh during run time. [default_value = “”]

exclude_install_path: Comma-separated list of installation paths to exclude from LD_LIBRARY_PATH, PYTHONPATH, and PATH environment variables. (/path/to/custom_ros_workspace/install/). [default_value = “”]

Now we will go through the main examples for running Isaac Sim from ROS 2 launch. Make sure to quit the launch process before the next example.

To launch Isaac Sim in default configuration run the command below.

ros2 launch isaacsim run_isaacsim.launch.py
To launch Isaac Sim with custom ROS packages in your workspace, run the command below.


Humble
ros2 launch isaacsim run_isaacsim.launch.py exclude_install_path:=/home/user/IsaacSim-ros_workspaces/humble_ws/install ros_installation_path:=/home/user/IsaacSim-ros_workspaces/build_ws/humble/humble_ws/install/local_setup.bash
Important

Due to Isaac Sim only supporting Python 3.12, we need to ensure that exclude_install_path parameter is set to the install folder of your workspace (for example: /home/user/IsaacSim-ros_workspaces/humble_ws/install) as that contains the incompatible Python 3.10 modules (for Ubuntu 22.04 only). Next, add the ros_installation_path parameter with path to the local_setup.bash file in your Python 3.12 build of your workspace.


Jazzy
Next we will launch Isaac Sim with a USD file open and immediately start playing. Run the command below.

ros2 launch isaacsim run_isaacsim.launch.py gui:=https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/Samples/ROS2/Robots/Nova_Carter_ROS.usd play_sim_on_start:=true
Now lets launch Isaac Sim with standalone workflow. Run the command below.

ros2 launch isaacsim run_isaacsim.launch.py standalone:=$HOME/isaacsim/standalone_examples/api/isaacsim.ros2.bridge/moveit.py
Launch Isaac Sim with Nav2
The Isaac Sim launch file can be included in other launch files to incorporate launching Isaac Sim from other ROS 2 workflows.

Here we will demonstrate launching Isaac Sim with the Nav2 example and the isaac_ros_navigation_goal ROS 2 package.

The example launch file can be found in the carter_navigation package in carter_navigation/launch/carter_navigation_isaacsim.launch.py.

In this scenario, the launch file is configured to wait for a console output from Isaac Sim: “Stage loaded and simulation is playing.”. This message is printed from the open_isaacsim_stage.py script which is used to load any scene in GUI mode. This is found in the scripts folder of isaacsim package.

Note

If running Isaac Sim in standalone workflow, you would need to add your own print statement that launch files can listen for and act accordingly.

Run the integrated launch file using the command below.

ros2 launch carter_navigation carter_navigation_isaacsim.launch.py
Wait a moment for the scene to load. After the warehouse navigation scene is automatically loaded in Isaac Sim, RViz2 will automatically begin displaying the robot’s sensor data and automatic goals will be generated for the robot to navigate towards.

Note

If the above demo fails activate automatic goals, it is possible that Nav2 has not initialized yet. A workaround for this issue is manually add a delay before launching the isaac_ros_navigation_goal package. You can do so by looking for execute_second_node_if_condition_met function inside of carter_navigation_isaacsim.launch.py and uncommenting the lines as explained in the comment.

You can run the same workflow using the iw_hub robot navigation scene and the iw_hub_navigation package. Run the integrated launch file using the following command:

ros2 launch iw_hub_navigation iw_hub_navigation_isaacsim.launch.py
Summary
In this tutorial, we covered

Launching Isaac Sim from a ROS 2 launch file.

Running an integrated launch file with Isaac Sim Nav2 stack, and isaac_ros_navigation_goal package.

