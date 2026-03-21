Multiple Robot Scenarios
Learning Objectives
This tutorial describes how to create and manage multiple robot scenarios in NVIDIA Isaac Sim. It explains how to use parameterization and Python classes to scale your simulations with multiple instances of robots performing similar tasks. After this tutorial, you will have more experience building scalable multi-robot simulations in NVIDIA Isaac Sim.

15-20 Minute Tutorial

Getting Started
Prerequisites

Review Adding Multiple Robots prior to beginning this tutorial.

Begin with the source code open from the previous tutorial, Adding Multiple Robots.

Note

Pressing STOP, then PLAY in this workflow might not reset the world properly. Use the RESET button instead.

Organizing Robot Scenarios with Classes
When working with multiple robots performing similar tasks, it’s helpful to encapsulate the robot setup and control logic into reusable classes. This approach allows you to easily create multiple instances with different parameters (like position offsets).

Create a RobotScenario class that manages a Jetbot pushing a cube to a Franka:

import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import Articulation, GeomPrim, RigidPrim, XformPrim
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.examples.base.base_sample_experimental import BaseSample
from isaacsim.robot.manipulators.examples.franka import FrankaExperimental
from isaacsim.storage.native import get_assets_root_path


class RobotScenario:
    """Encapsulates a Jetbot + Franka + Cube scenario with an offset."""

    def __init__(self, name: str, offset: np.ndarray = np.array([0.0, 0.0, 0.0])):
        self.name = name
        self.offset = offset
        self.state = 0
        self.step_counter = 0
        self.pick_phase = 0
        self.jetbot = None
        self.franka = None
        self.cube = None
        self.cube_goal = np.array([1.2, 0.0, 0.0]) + offset

    def setup_scene(self):
        """Create the robots and cube for this scenario."""
        assets_root_path = get_assets_root_path()
        base_path = f"/World/{self.name}"

        # Add Jetbot
        stage_utils.add_reference_to_stage(
            usd_path=assets_root_path + "/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd",
            path=f"{base_path}/Jetbot",
        )
        jetbot_xform = XformPrim(f"{base_path}/Jetbot")
        jetbot_xform.reset_xform_op_properties()
        jetbot_xform.set_world_poses(positions=[self.offset.tolist()])

        # Add cube in front of Jetbot
        cube_pos = self.offset + np.array([0.15, 0.0, 0.025])
        visual_material = PreviewSurfaceMaterial(f"{base_path}/Materials/red")
        visual_material.set_input_values("diffuseColor", [1.0, 0.0, 0.0])
        cube_shape = Cube(
            paths=f"{base_path}/Cube",
            positions=np.array([cube_pos]),
            sizes=[1.0],
            scales=np.array([[0.05, 0.05, 0.05]]),
            reset_xform_op_properties=True,
        )
        GeomPrim(paths=cube_shape.paths, apply_collision_apis=True)
        RigidPrim(paths=cube_shape.paths)
        cube_shape.apply_visual_materials(visual_material)

        # Add Franka
        franka_pos = self.offset + np.array([0.8, -0.3, 0.0])
        self.franka = FrankaExperimental(robot_path=f"{base_path}/Franka", create_robot=True)
        franka_xform = XformPrim(f"{base_path}/Franka")
        franka_xform.reset_xform_op_properties()
        franka_xform.set_world_poses(positions=[franka_pos.tolist()])

    def initialize(self):
        """Initialize articulation handles after scene load."""
        base_path = f"/World/{self.name}"
        self.jetbot = Articulation(f"{base_path}/Jetbot")
        self.cube = RigidPrim(f"{base_path}/Cube")

    def reset(self):
        """Reset the scenario state."""
        self.state = 0
        self.step_counter = 0
        self.pick_phase = 0
        self.franka.reset_to_default_pose()

    def step(self):
        """Execute one step of the scenario logic."""
        if self.state == 0:
            # Jetbot pushes cube
            cube_pos = self.cube.get_world_poses()[0].numpy()[0]
            if np.linalg.norm(cube_pos[:2] - self.cube_goal[:2]) > 0.05:
                self.jetbot.set_dof_velocity_targets([[10.0, 10.0]])
            else:
                self.jetbot.set_dof_velocity_targets([[0.0, 0.0]])
                self.state = 1
                self.step_counter = 0

        elif self.state == 1:
            # Jetbot backs up
            self.jetbot.set_dof_velocity_targets([[-8.0, -8.0]])
            self.step_counter += 1
            if self.step_counter > 100:
                self.jetbot.set_dof_velocity_targets([[0.0, 0.0]])
                self.state = 2
                self.step_counter = 0
                self.franka.open_gripper()

        elif self.state == 2:
            # Franka pick-and-place
            self._franka_pick_place()

    def _franka_pick_place(self):
        """Execute Franka pick-and-place state machine."""
        cube_pos = self.cube.get_world_poses()[0].numpy()[0]
        down_orient = self.franka.get_downward_orientation()
        self.step_counter += 1

        if self.pick_phase == 0:
            self.franka.set_end_effector_pose(np.array([[cube_pos[0], cube_pos[1], cube_pos[2] + 0.2]]), down_orient)
            if self.step_counter > 120:
                self.pick_phase = 1
                self.step_counter = 0
        elif self.pick_phase == 1:
            self.franka.set_end_effector_pose(np.array([[cube_pos[0], cube_pos[1], cube_pos[2] + 0.1]]), down_orient)
            if self.step_counter > 100:
                self.franka.close_gripper()
                self.pick_phase = 2
                self.step_counter = 0
        elif self.pick_phase == 2:
            self.franka.close_gripper()
            if self.step_counter > 50:
                self.pick_phase = 3
                self.step_counter = 0
        elif self.pick_phase == 3:
            self.franka.set_end_effector_pose(np.array([[cube_pos[0], cube_pos[1], cube_pos[2] + 0.25]]), down_orient)
            if self.step_counter > 100:
                self.pick_phase = 4
                self.step_counter = 0
        elif self.pick_phase == 4:
            target = self.offset + np.array([0.3, 0.3, 0.15])
            self.franka.set_end_effector_pose(np.array([target]), down_orient)
            if self.step_counter > 150:
                self.franka.open_gripper()
                self.step_counter = 0
                self.pick_phase = 5
        elif self.pick_phase == 5:
            # Lift the arm from target position (don't use cube_pos - cube was dropped)
            target = self.offset + np.array([0.3, 0.3, 0.4])  # Lift above drop location
            self.franka.set_end_effector_pose(np.array([target]), down_orient)
            if self.step_counter > 150:
                self.step_counter = 0
                self.state = 5  # Done


class HelloWorld(BaseSample):
    def __init__(self) -> None:
        super().__init__()
        self._physics_callback_id = None
        self._scenario = None

    def setup_scene(self):
        # Add ground plane
        stage_utils.add_reference_to_stage(
            usd_path=get_assets_root_path() + "/Isaac/Environments/Grid/default_environment.usd",
            path="/World/ground",
        )
        # Create a single scenario
        self._scenario = RobotScenario(name="scenario_0", offset=np.array([0.0, 0.0, 0.0]))
        self._scenario.setup_scene()

    async def setup_post_load(self):
        self._scenario.initialize()

        from isaacsim.core.simulation_manager.impl.isaac_events import IsaacEvents

        self._physics_callback_id = SimulationManager.register_callback(
            self.physics_step, IsaacEvents.POST_PHYSICS_STEP
        )

    def physics_step(self, dt, context):
        self._scenario.step()

    async def setup_post_reset(self):
        self._scenario.reset()

    def physics_cleanup(self):
        if self._physics_callback_id is not None:
            SimulationManager.deregister_callback(self._physics_callback_id)
            self._physics_callback_id = None
../_images/core_api_tutorials_6_1.webp
Scaling to Multiple Scenarios
import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import Articulation, GeomPrim, RigidPrim, XformPrim
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.examples.base.base_sample_experimental import BaseSample
from isaacsim.robot.manipulators.examples.franka import FrankaExperimental
from isaacsim.storage.native import get_assets_root_path

# RobotScenario class definition (same as above)
# ... (include the full RobotScenario class from the previous example)


class HelloWorld(BaseSample):
    def __init__(self) -> None:
        super().__init__()
        self._physics_callback_id = None
        self._scenarios = []
        self._num_scenarios = 2  # Number of parallel scenarios

    def setup_scene(self):
        # Add ground plane
        stage_utils.add_reference_to_stage(
            usd_path=get_assets_root_path() + "/Isaac/Environments/Grid/default_environment.usd",
            path="/World/ground",
        )

        # Create multiple scenarios with Y-axis offsets
        for i in range(self._num_scenarios):
            offset = np.array([0.0, (i - 1) * 2.0, 0.0])  # Spread along Y-axis
            scenario = RobotScenario(name=f"scenario_{i}", offset=offset)
            scenario.setup_scene()
            self._scenarios.append(scenario)

    async def setup_post_load(self):
        # Initialize all scenarios
        for scenario in self._scenarios:
            scenario.initialize()

        from isaacsim.core.simulation_manager.impl.isaac_events import IsaacEvents

        self._physics_callback_id = SimulationManager.register_callback(
            self.physics_step, IsaacEvents.POST_PHYSICS_STEP
        )

    def physics_step(self, dt, context):
        # Step all scenarios
        for scenario in self._scenarios:
            scenario.step()

    async def setup_post_reset(self):
        # Reset all scenarios
        for scenario in self._scenarios:
            scenario.reset()

    def physics_cleanup(self):
        if self._physics_callback_id is not None:
            SimulationManager.deregister_callback(self._physics_callback_id)
            self._physics_callback_id = None
        self._scenarios = []
../_images/core_api_tutorials_6_2.webp
Adding Randomization
To make simulations more interesting, you can add randomization to the scenario parameters. Modify the RobotScenario class to accept randomization options:

class RobotScenario:
    """Encapsulates a Jetbot + Franka + Cube scenario with randomization."""

    def __init__(self, name: str, offset: np.ndarray = np.array([0.0, 0.0, 0.0]), randomize: bool = False):
        self.name = name
        self.offset = offset
        self.randomize = randomize
        self.state = 0
        self.step_counter = 0
        self.pick_phase = 0

        # Randomize cube goal position if enabled
        if randomize:
            random_x = np.random.uniform(1.1, 1.4)
            self.cube_goal = np.array([random_x, 0.0, 0.0]) + offset
        else:
            self.cube_goal = np.array([1.2, 0.0, 0.0]) + offset

        # ... rest of the class remains the same
Then create scenarios with randomization enabled:

# Create multiple scenarios with randomization
for i in range(self._num_scenarios):
    offset = np.array([0.0, (i - 1) * 2.0, 0.0])
    scenario = RobotScenario(name=f"scenario_{i}", offset=offset, randomize=True)  # Enable randomization
    scenario.setup_scene()
    self._scenarios.append(scenario)
Best Practices for Scaling
When creating large-scale multi-robot simulations:

Use unique paths: Each scenario should use unique USD prim paths to avoid conflicts. The RobotScenario class uses the scenario name to create unique paths like /World/scenario_0/Jetbot.

Manage state independently: Each scenario instance maintains its own state variables, allowing scenarios to progress independently.

Clean up properly: The physics_cleanup method ensures callbacks are deregistered and scenario lists are cleared when the simulation is stopped.

Consider performance: With many scenarios, consider reducing physics step frequency or using GPU-accelerated simulation for better performance.

Summary
This tutorial covered the following topics:

Organizing robot scenarios into reusable Python classes

Using the offset parameter to position multiple scenarios in the world

Scaling to multiple parallel scenarios with a simple loop

Adding randomization to scenario parameters

Best practices for managing multiple robot instances