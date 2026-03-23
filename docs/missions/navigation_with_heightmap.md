ROS 2 Navigation with Heightmap Importer
Learning Objectives
In this example, you learn how to:

Generate a 3D world using a 2D occupancy map

Perform navigation with a robot in the generated 3D world with Nav2

Prerequisite

Completed ROS 2 Navigation for ROS 2 Nav2 with a single robot. So that

ROS 2 and Nav2 are installed, and ROS2 bridge is enabled.

Appropriate ros2_ws is sourced so that carter_navigation and isaac_ros_navigation_goal are inside your workspace.

Note

In Windows 10 or 11, depending on your machine’s configuration, RViz2 might not open properly.

Setting Up Environment and Robot
Generate 3D World
First, let us load the 3D world using the Heightmap Importer within Isaac Sim

Go to the top menu bar and click Tools > Robotics > Heightmap Importer.

Press Load Image button and open the image of the occupancy map located under carter_navigation/maps/carter_warehouse_navigation.png. A window titled Visualization will appear.

Press the Generate button to create geometry corresponding to the input occupancy map in the Stage.

The generated 3D terrain automatically has a collision mesh applied for all the occupied pixels.

Add Robot in Scene
Add a Carter robot, which has all ROS 2 OmniGraph Nodes setup, into this scene.

Go to the Isaac Sim Content browser and click Isaac Sim>Samples>ROS2>Robots.

Drag and drop the Nova_Carter_ROS.usd asset into the scene generated in the previous step (anywhere in the space bounded by the walls and on the ground)

Add Clock in Scene
To ensure all external ROS 2 nodes reference simulation time, a ROS_Clock graph needs to be added, which contains a Ros2PublishClock node responsible for publishing the simulation time to the /clock topic.

Follow the steps in Graph Shortcut to add a clock in the scene.

Running Navigation
We now have the 3D scene and robot set up to run the Nav2 stack.

Click on Play in Isaac Sim to begin simulation.

Open a new terminal and source the <ros2_ws> that contains the carter_navigation package. Run the ROS 2 launch file to begin Nav2.

ros2 launch carter_navigation carter_navigation.launch.py
RViz2 will open and begin loading the occupancy map. If a map does not appear, repeat the previous step.

Use the 2D Pose Estimate button to re-set the position of the robot. Make sure you do this before setting a goal and the pose estimate is approximately correct.

Click on the Navigation2 Goal button and then click and drag at the desired location point in the map. Nav2 will now generate a trajectory and the robot will start moving towards its destination.

Summary
In this tutorial, you:

Generated 3D world using 2D occupancy map with Heightmap Importer.

Added a robot into this world and running Nav2 with it.

Next Steps
Continue on to the next tutorial in our ROS2 Tutorials series, MoveIt 2 to learn how to connect the manipulator up with MoveIt 2.