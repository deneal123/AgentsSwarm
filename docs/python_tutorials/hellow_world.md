Hello World
NVIDIA Omniverse™ Kit, the toolkit that NVIDIA Isaac Sim uses to build its applications, provides a Python interpreter for scripting. This means every single GUI command, as well as many additional functions are available as Python APIs. However, the learning curve for interfacing with Omniverse Kit using Pixar’s USD Python API is steep and steps are frequently tedious. Therefore we’ve provided a set of APIs that are designed to be used in robotics applications, APIs that abstract away the complexity of USD APIs and merge multiple steps into one for frequently performed tasks.

In this tutorial, we will present the concepts of Core APIs and how to use them. We will start with adding a cube to an empty stage, and we’ll build upon it to create a scene with multiple robots executing multiple tasks simultaneously, as seen below.

../_images/core_api_tutorials_6_2.webp
Learning Objectives
This tutorial series introduces the Core API. After this tutorial, you learn:

How to use the Core APIs to manipulate the USD stage.

How to add a rigid body to the Stage and simulate it using Python in NVIDIA Isaac Sim.

The difference between running Python in an Extension Workflow vs a Standalone Workflow.

10-15 Minute Tutorial

Getting Started
Prerequisites

Intermediate knowledge in Python and asynchronous programming is required for this tutorial.

Please download and install Visual Studio Code prior to beginning this tutorial.

Please review Quick Tutorials and Workflows prior to beginning this tutorial.

Begin by opening the Hello World example. First activate Windows > Examples > Robotics Examples which will open the Robotics Examples tab.

Click Robotics Examples > General > Hello World.

Verify that the window for the Hello World example extension is visible in the workspace.

Click the Open Source Code button to launch the source code for editing in Visual Studio Code.

Click the Open Containing Folder button to open the directory containing the example files.

This folder contains three files: hello_world.py, hello_world_extension.py, and __init__.py.

The hello_world.py script is where the logic of the application will be added, while the UI elements of the application will be added in hello_world_extension.py script and thus linked to the logic.

Click the LOAD button to load the World.

click File > New From Stage Template > Empty to create a new stage, click Don’t Save when prompted to save the current stage.

Click the LOAD button to load the World again.

Open hello_world.py and press “Ctrl+S” to use the hot-reload feature. You will notice that the menu disappears from the workspace (because it was restarted).

Open the example menu again and click the LOAD button.

Now you can begin adding to this example.

Code Overview
This example inherits from BaseSample, which is a boilerplate extension application that sets up the basics for every robotics extension application. The following are a few examples of the actions BaseSample performs:

Loading assets into the stage using a button.

Clearing the stage when a new stage is created.

Resetting objects to their default states.

Handling hot reloading.

import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.examples.base.base_sample_experimental import BaseSample
from isaacsim.storage.native import get_assets_root_path


class HelloWorld(BaseSample):
    def __init__(self) -> None:
        super().__init__()

    # This function is called to setup the assets in the scene for the first time
    def setup_scene(self):
        # Add ground plane directly to the stage
        ground_plane = stage_utils.add_reference_to_stage(
            usd_path=get_assets_root_path() + "/Isaac/Environments/Grid/default_environment.usd",
            path="/World/ground",
        )
Key Concepts
Stage Utilities: The stage_utils module provides functions for directly manipulating the USD stage, such as adding references, creating prims, and managing stage hierarchy.

Prim Classes: The API provides prim wrapper classes like RigidPrim, GeomPrim, and Articulation that give you direct control over USD prims with physics capabilities.

SimulationManager: For callbacks and simulation events, the SimulationManager class provides methods to register and deregister callbacks for various simulation events.

Adding to the Scene
Use the Python API to add a cube as a rigid body to the scene. With the Core APIs, create the geometry first, then apply collision and rigid body properties.

import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
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

        # Create a blue visual material for the cube
        visual_material = PreviewSurfaceMaterial("/World/Materials/blue")
        visual_material.set_input_values("diffuseColor", [0.0, 0.0, 1.0])

        # Create the cube geometry
        self._cube_shape = Cube(
            paths="/World/fancy_cube",
            positions=np.array([[0.0, 0.0, 1.0]]),  # Starting position 1m above ground
            sizes=[1.0],
            scales=np.array([[0.5015, 0.5015, 0.5015]]),  # Scale the cube
            reset_xform_op_properties=True,
        )

        # Apply collision APIs to enable physics collision
        GeomPrim(paths=self._cube_shape.paths, apply_collision_apis=True)

        # Make it a rigid body (dynamic object that responds to physics)
        self._cube = RigidPrim(paths=self._cube_shape.paths)

        # Apply the blue material
        self._cube_shape.apply_visual_materials(visual_material)
Press Ctrl+S to save the code and hot-reload NVIDIA Isaac Sim.

Open the menu again.

click File > New From Stage Template > Empty, then the LOAD button. You need to perform this action if you change anything in the setup_scene. Otherwise, you only need to press the LOAD button.

See the dynamic cube falling as the simulation starts automatically.

../_images/core_api_tutorials_1_1.webp
Note

Every time the code is edited or changed, press Ctrl+S to save the code and hot-reload NVIDIA Isaac Sim.

Understanding the Prim Classes
The experimental API uses a layered approach to create physics-enabled objects:

Cube (or other shape classes): Creates the visual geometry on the USD stage.

GeomPrim: Wraps the geometry and can apply collision APIs for physics interactions.

RigidPrim: Adds rigid body dynamics, making the object respond to gravity and forces.

This modular approach gives you fine-grained control - you can create static colliders (GeomPrim without RigidPrim) or fully dynamic objects (with both).

Inspecting Object Properties
Print the world pose and velocity of the cube. The highlighted lines show how you can query object properties.

import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
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

        # Create a blue visual material for the cube
        visual_material = PreviewSurfaceMaterial("/World/Materials/blue")
        visual_material.set_input_values("diffuseColor", [0.0, 0.0, 1.0])

        # Create the cube geometry
        self._cube_shape = Cube(
            paths="/World/fancy_cube",
            positions=np.array([[0.0, 0.0, 1.0]]),
            sizes=[1.0],
            scales=np.array([[0.5015, 0.5015, 0.5015]]),
            reset_xform_op_properties=True,
        )

        # Apply collision and rigid body
        GeomPrim(paths=self._cube_shape.paths, apply_collision_apis=True)
        self._cube = RigidPrim(paths=self._cube_shape.paths)
        self._cube_shape.apply_visual_materials(visual_material)

    # This function is called after load button is pressed
    # It's called after setup_scene and after one physics time step
    # to propagate physics handles needed to retrieve physical properties
    async def setup_post_load(self):
        # Query cube properties using RigidPrim methods
        positions, orientations = self._cube.get_world_poses()
        # get_velocities() returns a tuple: (linear_velocities, angular_velocities)
        linear_velocities, angular_velocities = self._cube.get_velocities()

        # Convert from warp arrays to numpy for printing
        # Note: experimental APIs return batched results (even for single objects)
        print("Cube position is : " + str(positions.numpy()[0]))
        print("Cube's orientation is : " + str(orientations.numpy()[0]))
        print("Cube's linear velocity is : " + str(linear_velocities.numpy()[0]))
Note

The experimental APIs return batched results as warp arrays. Use .numpy() to convert them to numpy arrays, and index with [0] to get the first (and only) element when working with a single object.

Continuously Inspecting the Object Properties during Simulation
Print the world pose and velocity of the cube during simulation at every physics step executed. As mentioned in Workflows, in this workflow the application is running asynchronously and can’t control when to step physics. However, you can add callbacks to ensure certain things happen before certain events.

Add a physics callback using the SimulationManager:

import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
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

        # Create a blue visual material for the cube
        visual_material = PreviewSurfaceMaterial("/World/Materials/blue")
        visual_material.set_input_values("diffuseColor", [0.0, 0.0, 1.0])

        # Create the cube geometry
        self._cube_shape = Cube(
            paths="/World/fancy_cube",
            positions=np.array([[0.0, 0.0, 1.0]]),
            sizes=[1.0],
            scales=np.array([[0.5015, 0.5015, 0.5015]]),
            reset_xform_op_properties=True,
        )

        # Apply collision and rigid body
        GeomPrim(paths=self._cube_shape.paths, apply_collision_apis=True)
        self._cube = RigidPrim(paths=self._cube_shape.paths)
        self._cube_shape.apply_visual_materials(visual_material)

    async def setup_post_load(self):
        # Register a physics callback using SimulationManager
        from isaacsim.core.simulation_manager.impl.isaac_events import IsaacEvents

        self._physics_callback_id = SimulationManager.register_callback(
            self.print_cube_info, IsaacEvents.POST_PHYSICS_STEP
        )

    # Physics callback function - called after each physics step
    # Takes dt (delta time) and context as arguments
    def print_cube_info(self, dt, context):
        positions, orientations = self._cube.get_world_poses()
        linear_velocities, angular_velocities = self._cube.get_velocities()

        print("Cube position is : " + str(positions.numpy()[0]))
        print("Cube's orientation is : " + str(orientations.numpy()[0]))
        print("Cube's linear velocity is : " + str(linear_velocities.numpy()[0]))

    def physics_cleanup(self):
        # Clean up callback when the extension is unloaded
        if self._physics_callback_id is not None:
            SimulationManager.deregister_callback(self._physics_callback_id)
            self._physics_callback_id = None
Converting the Example to a Standalone Application
Note

On windows use python.bat instead of python.sh

The details of how python.sh works below are similar to how python.bat works

As mentioned in Workflows, in this workflow, the robotics application is started when launched from Python right away.

Open a new my_application.py file and add the following:

# Launch Isaac Sim before any other imports
# Default first two lines in any standalone application
from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})  # we can also run as headless

# Now import Isaac Sim modules
import isaacsim.core.experimental.utils.stage as stage_utils
import numpy as np
import omni.timeline
from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
from isaacsim.core.experimental.objects import Cube
from isaacsim.core.experimental.prims import GeomPrim, RigidPrim
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.storage.native import get_assets_root_path

# Add ground plane
ground_plane = stage_utils.add_reference_to_stage(
    usd_path=get_assets_root_path() + "/Isaac/Environments/Grid/default_environment.usd",
    path="/World/ground",
)

# Create a blue visual material for the cube
visual_material = PreviewSurfaceMaterial("/World/Materials/blue")
visual_material.set_input_values("diffuseColor", [0.0, 0.0, 1.0])

# Create the cube geometry
cube_shape = Cube(
    paths="/World/fancy_cube",
    positions=np.array([[0.0, 0.0, 1.0]]),
    sizes=[1.0],
    scales=np.array([[0.5, 0.5, 0.5]]),
    reset_xform_op_properties=True,
)

# Apply collision and rigid body
GeomPrim(paths=cube_shape.paths, apply_collision_apis=True)
cube = RigidPrim(paths=cube_shape.paths)
cube_shape.apply_visual_materials(visual_material)

# Start the timeline (physics simulation)
omni.timeline.get_timeline_interface().play()
simulation_app.update()

# Run the simulation loop
for i in range(50):
    # Only query when physics is actively simulating
    if SimulationManager.is_simulating():
        positions, orientations = cube.get_world_poses()
        linear_velocities, angular_velocities = cube.get_velocities()

        # Will be shown on terminal
        print("Cube position is : " + str(positions.numpy()[0]))
        print("Cube's orientation is : " + str(orientations.numpy()[0]))
        print("Cube's linear velocity is : " + str(linear_velocities.numpy()[0]))

    # Step the app (physics + rendering)
    simulation_app.update()

simulation_app.close()  # close Isaac Sim
Run it using ./python.sh ./exts/isaacsim.examples.interactive/isaacsim/examples/interactive/user_examples/my_application.py.

Summary
This tutorial covered the following topics:

Overview of the Core APIs for direct stage manipulation.

Using stage_utils to add assets to the stage.

Creating dynamic objects with Cube, GeomPrim, and RigidPrim.

Registering physics callbacks with SimulationManager.

Accessing dynamic properties for objects using prim wrapper methods.

The main differences in a standalone application.

Next Steps
Continue to Hello Robot to learn how to add a robot to the simulation.

Note

The next tutorials will be developed mainly using the extensions application workflow. However, conversion to other workflows is similar given what was covered in this tutorial.