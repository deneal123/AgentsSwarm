NameOverride Attribute
Learning Objectives
In this tutorial, you learn more about the isaac:nameOverride prim attribute and how it can be used for publishing joint names and TF.

Getting Started
Prerequisite

Completed Workflows to understand the Extension Workflow.

Completed ROS2 Joint Control: Extension Python Scripting to understand how to setup Joint Publishers and Subscribers.

Completed ROS2 Transform Trees and Odometry to understand how to setup TF Publishers.

Appropriate ros2_ws is sourced in the terminal that will be running Python scripts.

If running multiple machines, ensure FASTRTPS_DEFAULT_PROFILES_FILE environmental variable is set prior to launching sim, and ROS2 bridge is enabled.

Setting up the NameOverride Attribute
When setting up the Joint State or TF publishers, the prim name is used to publish the ROS link name. In some cases the prim names might not match the convention expected by the ROS stack. In this case, the isaac:nameOverride prim attribute allows you to internally override any prim name when it is used to publish using ROS.

Before proceeding, setup the scene by following the Add Joint States in Extension section.

Adding the isaac:nameOverride Prim Attribute
Click on any joint prim.

Look for the Name Override field in the raw USD properties in the property panel. If this field is already present, skip the following step and proceed to the next step thereafter. If this field is not present, proceed to the following step.

In the property panel, click Add. In the popup menu, go to Isaac > NameOverride. This will apply this attribute to the prim.

In the property panel, add your custom prim name in the Name Override field.

Click Play and notice the joint names have updated with the custom names you added when you echo the /joint_states topic.

ROS Publishers:

The ROS 2 Publish Transform Tree and the ROS 2 Publish Joint State OmniGraph node will automatically publish the name provided by the isaac:nameOverride attribute if it is defined for a given prim.

ROS Subscribers:

For the ROS 2 Joint State Subscriber pipeline, you can drag in the Isaac Joint Name Resolver OmniGraph node and connect it within the pipeline as shown below:

ROS2 Joint State Subscriber pipeline with NameOverride attribute
For the Isaac Joint Name Resolver node, set the Target Prim or the Robot Path to /panda.

If you publish joint commands to Isaac Sim from an external ROS 2 node using your custom prim names, the Isaac Joint Name Resolver node will provide the actual prim paths to the Articulation Controller, which will then be able to manipulate the prims as commanded.

Summary
This tutorial covered adding the isaac:nameOverride attribute to prims to enable custom names for each prim to be published and manipulated using ROS.

Next Steps
Continue on to the next tutorial in our ROS2 Tutorials series, ROS 2 Ackermann Controller to learn how to setup a Ackermann controller for your robot.