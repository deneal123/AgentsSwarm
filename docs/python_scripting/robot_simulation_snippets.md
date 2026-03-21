Robot Simulation Snippets
Hint

Refer to the Articulation class documentation for more details on the API.

Wrapping Articulations
Note

The following snippets should only be run once on a new stage. Create a new stage (File > New menu) and run the snippets in the Script Editor (Window > Script Editor menu).

Adds two Franka robots to the stage and wraps them via an Articulation object to control them simultaneously.

import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.core.experimental.prims import Articulation
from isaacsim.storage.native import get_assets_root_path

# Add Franka robots to the stage
usd_path = get_assets_root_path() + "/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd"
variants = [("Gripper", "AlternateFinger"), ("Mesh", "Quality")]
stage_utils.add_reference_to_stage(usd_path, path="/World/Franka_1", variants=variants)
stage_utils.add_reference_to_stage(usd_path, path="/World/Franka_2", variants=variants)

# Wrap Franka robots via an Articulation object
articulations = Articulation(
    "/World/Franka_.*",
    positions=[[-1, -1, 0], [1, 1, 0]],
    reset_xform_op_properties=True,
)
Play the simulation. Then, open a new tab in the Script Editor window (Tab > Add Tab menu) and execute the following code to set the DOF positions for each articulation.

# Set the joint positions for each articulation
articulations.set_dof_position_targets(
    [
        [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 0.0, 0.0],
        [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, 0.04, 0.04],
    ]
)
DOF Control
Note

The following snippets should only be run once on a new stage that has the Franka robot at the /Franka prim path, and while the simulation is playing.

Prepare the scene:

Add a Franka robot to the stage via the Create > Robots > Franka Emika Panda Arm menu.

Play the simulation.

Warning

The snippets are disparate examples, running them out of order may have unintended consequences. The resulting movements may not respect the robot’s kinematic limitations.

Make sure there is a Franka robot at the /Franka prim path and that the simulation is playing. Then, open the Script Editor window (Window > Script Editor menu) and run the following snippets.

Query Articulation
from isaacsim.core.experimental.prims import Articulation

articulation = Articulation("/Franka")
# Get articulation information
print("DOF count:", articulation.num_dofs)
print("DOF names:", articulation.dof_names)
print("DOF paths:", articulation.dof_paths)
print("DOF types:", articulation.dof_types)
print("Link count:", articulation.num_links)
print("Link names:", articulation.link_names)
print("Link paths:", articulation.link_paths)
Read DOF States
from isaacsim.core.experimental.prims import Articulation

articulation = Articulation("/Franka")
# Get all DOF states
print("DOF positions:", articulation.get_dof_positions())
print("DOF velocities:", articulation.get_dof_velocities())
print("DOF efforts:", articulation.get_dof_efforts())
DOF Position Control
import numpy as np
from isaacsim.core.experimental.prims import Articulation

articulation = Articulation("/Franka")
# Set all DOF positions to random values between -1 and 1
articulation.set_dof_position_targets(np.random.rand(9) * 2 - 1)
Single DOF Position Control
import numpy as np
from isaacsim.core.experimental.prims import Articulation

articulation = Articulation("/Franka")
# Set the 'panda_finger_joint1' DOF position to 0.04.
# The 'panda_finger_joint2' will mimic the value, as they are linked
articulation.set_dof_position_targets(0.04, dof_indices=articulation.get_dof_indices("panda_finger_joint1"))
DOF Velocity Control
import numpy as np
from isaacsim.core.experimental.prims import Articulation

articulation = Articulation("/Franka")
# Switch to velocity control mode
articulation.switch_dof_control_mode("velocity")
# Set all DOF velocities to random values between -10 and 10
articulation.set_dof_velocity_targets(10 * (np.random.rand(9) * 2 - 1))
Single DOF Velocity Control
import numpy as np
from isaacsim.core.experimental.prims import Articulation

articulation = Articulation("/Franka")
# Switch to velocity control mode
articulation.switch_dof_control_mode("velocity")
# Set the 'panda_joint4' DOF velocity to 0.25
articulation.set_dof_velocity_targets(0.25, dof_indices=articulation.get_dof_indices("panda_joint4"))
DOF Effort Control
import numpy as np
from isaacsim.core.experimental.prims import Articulation

articulation = Articulation("/Franka")
# Switch to effort control mode
articulation.switch_dof_control_mode("effort")
# Set all DOF efforts to random values between -100 and 100
articulation.set_dof_efforts(100 * (np.random.rand(9) * 2 - 1))