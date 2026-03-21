Hello Robot
Learning Objectives
This tutorial details how to add and move a mobile robot in NVIDIA Isaac Sim in an extension application. After this tutorial, you will understand how to add a robot to the simulation and apply actions to its wheels using Python.

10-15 Minute Tutorial

Getting Started
Prerequisites

Review Hello World prior to beginning this tutorial.

Begin with the source code of the Hello World example developed in the previous tutorial: Hello World.

Adding a Robot
Begin by adding a NVIDIA Jetbot to the scene, which allows you to access the library of NVIDIA Isaac Sim robots, sensors, and environments located on a Omniverse Nucleus Server using Python, as well as navigate through it using the Content window.

Note

The server shown in these steps has been connected to in Workstation Setup. Follow these steps first before proceeding.

../_images/core_api_tutorials_2_1.webp
Add the assets by simply dragging them to the stage window or the viewport.

Try to do the same thing through Python in the Hello World example.

Create a new stage: File > new > Don’t Save

Open the hello_world.py file by clicking the Open Source Code button in the Hello World window.

import carb
import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.core.experimental.prims import Articulation
from isaacsim.examples.base.base_sample_experimental import BaseSample
from isaacsim.storage.native import get_assets_root_path


class HelloWorld(BaseSample):
    def __init__(self) -> None:
        super().__init__()

    def setup_scene(self):
        # Add ground plane
        ground_plane = stage_utils.add_reference_to_stage(
            usd_path=get_assets_root_path() + "/Isaac/Environments/Grid/default_environment.usd",
            path="/World/ground",
        )

        # Get the assets root path from the Nucleus server
        assets_root_path = get_assets_root_path()
        if assets_root_path is None:
            carb.log_error("Could not find nucleus server with /Isaac folder")
            return

        # Add the Jetbot robot to the stage
        asset_path = assets_root_path + "/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd"
        stage_utils.add_reference_to_stage(usd_path=asset_path, path="/World/Fancy_Robot")

    async def setup_post_load(self):
        # Wrap the Jetbot with the Articulation class for control
        self._jetbot = Articulation("/World/Fancy_Robot")

        # Print info about the Jetbot
        print("Number of DOFs: " + str(self._jetbot.num_dofs))
        print("DOF names: " + str(self._jetbot.dof_names))
        print("Joint Positions: " + str(self._jetbot.get_dof_positions().numpy()))
Click the LOAD button to load the scene and see the Jetbot appear. Although it is being simulated, it is not moving. The next section walks through how to make the robot move.

Move the Robot
In NVIDIA Isaac Sim, Robots are constructed of physically accurate articulated joints. Applying actions to these articulations make them move.

Next, apply random velocities to the Jetbot’s wheel joints to get it moving.

import carb
import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
from isaacsim.core.experimental.prims import Articulation
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.examples.base.base_sample_experimental import BaseSample
from isaacsim.storage.native import get_assets_root_path


class HelloWorld(BaseSample):
    def __init__(self) -> None:
        super().__init__()
        self._physics_callback_id = None

    def setup_scene(self):
        # Add ground plane
        ground_plane = stage_utils.add_reference_to_stage(
            usd_path=get_assets_root_path() + "/Isaac/Environments/Grid/default_environment.usd",
            path="/World/ground",
        )

        # Get the assets root path from the Nucleus server
        assets_root_path = get_assets_root_path()
        if assets_root_path is None:
            carb.log_error("Could not find nucleus server with /Isaac folder")
            return

        # Add the Jetbot robot to the stage
        asset_path = assets_root_path + "/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd"
        stage_utils.add_reference_to_stage(usd_path=asset_path, path="/World/Fancy_Robot")

    async def setup_post_load(self):
        # Wrap the Jetbot with the Articulation class for control
        self._jetbot = Articulation("/World/Fancy_Robot")

        # Register a physics callback to send actions every physics step
        from isaacsim.core.simulation_manager.impl.isaac_events import IsaacEvents

        self._physics_callback_id = SimulationManager.register_callback(
            self.send_robot_actions, IsaacEvents.POST_PHYSICS_STEP
        )

    def send_robot_actions(self, dt, context):
        # Apply random velocity targets to the wheel joints
        # Jetbot has 2 DOFs: left_wheel_joint and right_wheel_joint
        random_velocities = 5 * np.random.rand(1, 2)  # Shape: (1, num_dofs)
        self._jetbot.set_dof_velocity_targets(random_velocities)

    def physics_cleanup(self):
        # Clean up callback when the extension is unloaded
        if self._physics_callback_id is not None:
            SimulationManager.deregister_callback(self._physics_callback_id)
            self._physics_callback_id = None
Click the LOAD button to load the scene and watch the Jetbot move with random velocities.

Note

Pressing STOP, then PLAY in this workflow might not reset the world properly. Use the RESET button instead.

Extra Practice
This example applies random velocities to the Jetbot articulation controller. Try the following exercises:

Make the Jetbot move backwards (hint: use negative velocities).

Make the Jetbot turn right (hint: apply different velocities to each wheel).

Make the Jetbot stop after 5 seconds (hint: track elapsed time in the callback).

Controlling Specific Joints
You can also control specific joints by their names or indices. Here’s how to get the wheel joint indices and apply velocities only to specific joints:

import carb
import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
from isaacsim.core.experimental.prims import Articulation
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.examples.base.base_sample_experimental import BaseSample
from isaacsim.storage.native import get_assets_root_path


class HelloWorld(BaseSample):
    def __init__(self) -> None:
        super().__init__()
        self._physics_callback_id = None

    def setup_scene(self):
        # Add ground plane
        ground_plane = stage_utils.add_reference_to_stage(
            usd_path=get_assets_root_path() + "/Isaac/Environments/Grid/default_environment.usd",
            path="/World/ground",
        )

        # Add the Jetbot robot to the stage
        assets_root_path = get_assets_root_path()
        asset_path = assets_root_path + "/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd"
        stage_utils.add_reference_to_stage(usd_path=asset_path, path="/World/Fancy_Robot")

    async def setup_post_load(self):
        # Wrap the Jetbot with the Articulation class
        self._jetbot = Articulation("/World/Fancy_Robot")

        # Print available DOF names
        print("Available DOFs:", self._jetbot.dof_names)

        # Get indices for specific wheel joints
        self._wheel_indices = self._jetbot.get_dof_indices(["left_wheel_joint", "right_wheel_joint"]).numpy()
        print("Wheel indices:", self._wheel_indices)

        # Register physics callback
        from isaacsim.core.simulation_manager.impl.isaac_events import IsaacEvents

        self._physics_callback_id = SimulationManager.register_callback(
            self.send_robot_actions, IsaacEvents.POST_PHYSICS_STEP
        )

    def send_robot_actions(self, dt, context):
        # Apply velocity targets to specific DOF indices
        wheel_velocities = np.array([[10.0, 10.0]])  # Both wheels same speed = forward
        self._jetbot.set_dof_velocity_targets(wheel_velocities, dof_indices=self._wheel_indices)

    def physics_cleanup(self):
        if self._physics_callback_id is not None:
            SimulationManager.deregister_callback(self._physics_callback_id)
            self._physics_callback_id = None
../_images/core_api_tutorials_2_2.webp
Summary
This tutorial covered the following topics:

Adding NVIDIA Isaac Sim library components from a Nucleus Server

Adding a robot to the stage using stage_utils.add_reference_to_stage()

Wrapping a robot with the Articulation class for control

Using set_dof_velocity_targets() to apply velocity control

Registering physics callbacks with SimulationManager

Controlling specific joints by name or index

Next Steps
Continue on to the next tutorial in the Essential Tutorials series, Adding a Manipulator Robot, to learn how to add a manipulator robot to the simulation.

Further Learning
Nucleus Server

For an overview of how to best leverage a Nucleus Server, see the Nucleus Overview in NVIDIA Omniverse tutorial.

Robot Specific Extensions

NVIDIA Isaac Sim provides several robot extensions such as isaacsim.robot.manipulators.examples.franka, isaacsim.robot.manipulators.examples.universal_robots, and many more. To learn more, check out the standalone examples located at standalone_examples/api/isaacsim.robot.manipulators/franka and standalone_examples/api/isaacsim.robot.manipulators/universal_robots/.