ROS 2 Bridge in Standalone Workflow
Learning Objectives
Run standalone ROS2 Python examples

Manually step ROS2 components

Getting Started
Prerequisite

Completed Workflows and Hello World to understand the two workflows (Standalone and Extension).

Set the environment variables needed to enable ROS2 messaging in standalone workflow by completing the steps in Using Terminal or Enable ROS 2 Python Standalone Scripts.

Note

In Windows 10 or 11, depending on your machine’s configuration, RViz2 might not open properly.

Manually Stepping ROS2 Components
Standalone scripting is typically ideal for manual control of the simulation steps. An OnImpulseEvent OmniGraph node can be connected to any ROS2 OmniGraph node so that the frequency of the publishers and subscribers can be carefully controlled.

An example of how a new action graph with a ROS2 Publish Clock node can be setup to be precisely controlled with a ROS2 Domain ID of 1:

import omni.graph.core as og

# Create a new graph with the path /ActionGraph
og.Controller.edit(
    {"graph_path": "/ActionGraph", "evaluator_name": "execution"},
    {
        og.Controller.Keys.CREATE_NODES: [
            ("ReadSimTime", "isaacsim.core.nodes.IsaacReadSimulationTime"),
            ("Context", "isaacsim.ros2.bridge.ROS2Context"),
            ("PublishClock", "isaacsim.ros2.bridge.ROS2PublishClock"),
            ("OnImpulseEvent", "omni.graph.action.OnImpulseEvent"),
        ],
        og.Controller.Keys.CONNECT: [
            # Connecting execution of OnImpulseEvent node to PublishClock so it will only publish when an impulse event is triggered
            ("OnImpulseEvent.outputs:execOut", "PublishClock.inputs:execIn"),
            # Connecting simulationTime data of ReadSimTime to the clock publisher node
            ("ReadSimTime.outputs:simulationTime", "PublishClock.inputs:timeStamp"),
            # Connecting the ROS2 Context to the clock publisher node so it will run under the specified ROS2 Domain ID
            ("Context.outputs:context", "PublishClock.inputs:context"),
        ],
        og.Controller.Keys.SET_VALUES: [
            # Assigning topic name to clock publisher
            ("PublishClock.inputs:topicName", "/clock"),
            # Assigning a Domain ID of 1 to Context node
            ("Context.inputs:domain_id", 1),
            # Disable useDomainIDEnvVar to ensure we use the above set Domain ID
            ("Context.inputs:useDomainIDEnvVar", False),
        ],
    },
)
On any frame, run the following to set an impulse event, which will tick the clock publisher once:

og.Controller.set(og.Controller.attribute("/ActionGraph/OnImpulseEvent.state:enableImpulse"), True)
Note

Due to the explicit control of rendering and physics simulation steps in standalone scripting, the time it takes to complete each step will depend on the computation load and will likely not match real time. This might cause a discrepancy in observed speed of action when running the same application using standalone scripting versus using the GUI. When that occurs, use the simulation clock as reference.

Examples
A few of the tutorial examples were transformed into standalone Python examples. Here are the instructions for running them.

ROS 2 Clock
This sample demonstrates how to create a action graph with ROS 2 component nodes and then tick them at different rates.

The sample can be executed by running the following:

./python.sh standalone_examples/api/isaacsim.ros2.bridge/clock.py
Echo the following topics to observe messages being published:

ros2 topic echo /sim_time
ros2 topic echo /manual_time
To create and set up a ROS 2 Clock publisher using the Isaac Sim UI, refer to the ROS 2 Clock tutorial.

ROS 2 Camera
The following two samples demonstrates how to create a action graph with ROS 2 Camera Helper and Camera Info Helper OmniGraph nodes, which are used to setup ROS 2 RGB image, depth image, and camera info publishers. Both samples accomplish the same outcome of publishing ROS 2 image data at different rates but use different solutions.

On each frame:

Camera Info is published

Every 5 frames:

RGB image is published

Every 60 frames:

Depth image is published

Periodic Image Publishing
The execution rate (every N frames) for each of the ROS 2 image and camera info publishers are set by modifying their respective Isaac Simulation Gate OmniGraph nodes in the SDGPipeline graph. By setting the execution rate, an image publisher will automatically be ticked every N rendered frames.

The sample can be executed by running the following:

./python.sh standalone_examples/api/isaacsim.ros2.bridge/camera_periodic.py
To exit the sample, you can terminate the process using CTRL-C from the terminal.

Manual Image Publishing
The ROS 2 image and camera info publishers are manually controlled by injecting Branch OmniGraph nodes between each publisher node and their respective Isaac Simulation Gate OmniGraph node. The Branch nodes act like a custom gate and can be enabled or disabled at any time. Whenever a Branch node is enabled, the connected ROS 2 publisher node will be ticked.

The sample can be executed by running the following:

./python.sh standalone_examples/api/isaacsim.ros2.bridge/camera_manual.py
To exit the sample, you can terminate the process using CTRL-C from the terminal.

Visualizing Results
To visualize the result of either sample in RViz2, in a new ROS2-sourced terminal navigate to the Isaac Sim package directory and run the following command:

rviz2 -d <ros2_ws>/src/isaac_tutorials/rviz2/camera_manual.rviz
Note

Due to an issue with RViz2, black frames might appear for depth image displays. To verify that Isaac Sim is correctly publishing depth images, run ros2 run rqt_image_view rqt_image_view and set the topic to /depth.

Carter Stereo
This sample demonstrates how to take an existing USD stage with an action graph containing ROS 2 component nodes and modifying the default settings. The stereo camera pair is automatically enabled and the second viewport window is docked in the UI.

On each frame:

The ROS 2 clock is published

A ROS 2 PointCloud2 message originating from an RTX Lidar is published

Odometry is published

The Twist subscriber is spun

TF messages are published

Left and right cameras are published

Every Two Frames:

The Twist command message is published

The sample can be executed by running the following:

./python.sh standalone_examples/api/isaacsim.ros2.bridge/carter_stereo.py
To exit the sample, you can terminate the process using CTRL-C from the terminal.

To visualize the result:

In a new terminal, run the following command to load RViz2:

rviz2 -d <ros2_ws>/src/isaac_tutorials/rviz2/carter_stereo.rviz
Make sure Right Camera - RGB and Left Camera - RGB within the Displays are enabled to visualize RGB images.

Note

If some of the images don’t show up on RViz2, press Stop and Play in the simulator for the images to show up.

Multiple Robot ROS 2 Navigation
This sample shows how to run an existing USD stage.

To visualize the output refer to the interactive version of the sample:

On each frame:

The ROS 2 clock component is published

ROS 2 PointCloud2 messages originating from RTX Lidars are published

Odometry is published

The Twist subscriber is spun

TF messages are published

The sample can be executed with both the hospital and office environments. Run either of the following commands to run the sample with the specified environment:


Hospital Environment
./python.sh standalone_examples/api/isaacsim.ros2.bridge/carter_multiple_robot_navigation.py --environment hospital

Office Environment
To exit the sample, you can terminate the process using CTRL-C from the terminal.

Note

If you encounter any issues, refer to Troubleshooting.

MoveIt2
This sample shows how to add multiple USD stages. It also demonstrates how to manually create a action graph with ROS 2 component nodes and then manually tick them.

To visualize the output refer to the interactive version of the sample:

On each frame:

The ROS 2 clock is published

Joint State messages are published

Joint State subscriber is spun

TF messages are published

The sample can be executed by running the following:

./python.sh standalone_examples/api/isaacsim.ros2.bridge/moveit.py
To exit the sample you can terminate using the terminal with CTRL-C

Receiving ROS 2 Messages
This is a basic subscriber example where upon receiving an empty ROS2 message, a cube in the scene teleports to a random location. This one is running with rendering enabled, you can verify that you observe the scene and the cube moving. To run this example:

./python.sh standalone_examples/api/isaacsim.ros2.bridge/subscriber.py
To exit the sample, you can terminate the process using CTRL-C from the terminal.

After the scene with cube is loaded, you can publish the empty message manually from another terminal. Use the rate of 1Hz.

ros2 topic pub -r 1 /move_cube std_msgs/msg/Empty
Summary
In this tutorial you learned how to manually step ROS 2 components and run standalone ROS 2 Python examples.

Next Steps
Continue on to the next tutorial in our ROS 2 Tutorials series, ROS 2 Navigation to learn to use ROS 2 Nav2 with NVIDIA Isaac Sim.