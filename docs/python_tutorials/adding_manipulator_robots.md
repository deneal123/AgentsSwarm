Adding a Manipulator Robot
Learning Objectives
This tutorial introduces a manipulator robot to the simulation, a Franka Panda. It describes how to add the robot to the scene and execute a pick-and-place operation. After this tutorial, you will have more experience using manipulator robots and controlling them with inverse kinematics in NVIDIA Isaac Sim.

15-20 Minute Tutorial

Getting Started
Prerequisites

Review Hello Robot prior to beginning this tutorial.

This tutorial uses standalone Python scripts. Run them with a Python environment where Isaac Sim is installed:

Creating the Scene with a Franka Robot
Add a Franka robot and a cube for the robot to pick up using the FrankaExperimental class. This class inherits from Articulation and provides high-level control methods including inverse kinematics and gripper control.

When you set create_robot=True in the constructor, FrankaExperimental automatically spawns the Franka robot USD asset at the specified path.

"""Create a scene with ground, Franka robot, and blue cube."""

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.robot.manipulators.examples.franka import FrankaExperimental
from isaacsim.storage.native import get_assets_root_path

DEVICE = "cpu"

assets_root_path = get_assets_root_path()

# Add ground plane
stage_utils.add_reference_to_stage(
    usd_path=assets_root_path + "/Isaac/Environments/Grid/default_environment.usd",
    path="/World/ground",
)

# Create the Franka robot
robot = FrankaExperimental(robot_path="/World/robot", create_robot=True)

# Create a blue cube for the robot to pick up
visual_material = PreviewSurfaceMaterial("/World/Materials/blue")
visual_material.set_input_values("diffuseColor", [0.0, 0.0, 1.0])
cube_shape = Cube(
    paths="/World/Cube",
    positions=[0.5, 0.0, 0.0258],
    sizes=1.0,
    scales=[0.0515, 0.0515, 0.0515],
)
GeomPrim(paths=cube_shape.paths, apply_collision_apis=True)
RigidPrim(paths=cube_shape.paths)
cube_shape.apply_visual_materials(visual_material)

SimulationManager.setup_simulation(dt=1.0 / 60.0, device=DEVICE)
physics_scene = SimulationManager.get_physics_scenes()[0]
physics_scene.set_enabled_gpu_dynamics(False)
app_utils.play()
app_utils.update_app(steps=20)

while simulation_app.is_running():
    simulation_app.update()

app_utils.stop()
simulation_app.close()
Run the script. A window opens with the Franka robot and cube in the scene; the simulation runs until you close the window.

The FrankaExperimental class provides these key methods for robot control:

set_end_effector_pose(position, orientation) - Move end-effector using inverse kinematics

open_gripper() / close_gripper() - Control the gripper

get_current_state() - Get DOF positions and end-effector pose

get_downward_orientation() - Get quaternion for downward-facing orientation

reset_to_default_pose() - Reset robot to home position

Using FrankaPickPlace for Complete Pick-and-Place
For a complete pick-and-place operation, use the FrankaPickPlace class. This class has a setup_scene() method that spawns everything needed for pick-and-place: the Franka robot, ground plane, and a cube to manipulate.

"""Pick-and-place using FrankaPickPlace."""

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.robot.manipulators.examples.franka import FrankaPickPlace
from isaacsim.storage.native import get_assets_root_path

DEVICE = "cpu"

assets_root_path = get_assets_root_path()

stage_utils.set_stage_up_axis("Z")
stage_utils.set_stage_units(meters_per_unit=1.0)
stage_utils.add_reference_to_stage(
    usd_path=assets_root_path + "/Isaac/Environments/Grid/default_environment.usd",
    path="/World/ground",
)

# FrankaPickPlace spawns robot and cube, and provides the pick-place state machine
controller = FrankaPickPlace()
controller.setup_scene()

SimulationManager.setup_simulation(dt=1.0 / 60.0, device=DEVICE)
physics_scene = SimulationManager.get_physics_scenes()[0]
physics_scene.set_enabled_gpu_dynamics(False)
app_utils.play()
# Run a few steps so the articulation's physics tensor entity is valid before `controller.reset()`
app_utils.update_app(steps=20)
controller.reset()

# Main loop: run one pick-place step each physics frame until done
while simulation_app.is_running():
    simulation_app.update()
    if app_utils.is_playing():
        if not controller.is_done():
            controller.forward()
        else:
            print("Pick-and-place completed")
            app_utils.pause()

app_utils.stop()
simulation_app.close()
Run the script. The robot automatically executes all phases of picking up and placing the cube.

Customizing the FrankaPickPlace Scene
The setup_scene() method accepts parameters to customize the cube position, size, and target position:

controller = FrankaPickPlace()
controller.setup_scene(
    cube_initial_position=[0.4, 0.2, 0.0258], cube_size=[0.05, 0.05, 0.05], target_position=[-0.4, 0.2, 0.12]
)
Understanding the Pick-and-Place State Machine
The FrankaPickPlace class uses a state machine with the following phases:

Pick-and-Place Phases
Phase

Description

Default Steps

0

Move to x,y position above cube

60

1

Approach down to cube

40

2

Close gripper to grasp

20

3

Lift cube upward

40

4

Move cube to target location

80

5

Open gripper to release

20

6

Move up and away

20

You can customize the phase durations by passing events_dt to the constructor:

# Custom phase durations (steps for each phase)
controller = FrankaPickPlace(events_dt=[80, 60, 30, 60, 100, 30, 30])
../_images/core_api_tutorials_4_1.webp
Summary
This tutorial covered the following topics:

Adding a Franka manipulator robot using FrankaExperimental with create_robot=True

Using the FrankaPickPlace.setup_scene() method to spawn a complete pick-and-place scene

Executing pick-and-place operations with the forward() method

Understanding and customizing the pick-and-place state machine phases

Next Steps
Continue to the next tutorial in our Essential Tutorials series, Adding Multiple Robots, to learn how to add multiple robots to the simulation.

