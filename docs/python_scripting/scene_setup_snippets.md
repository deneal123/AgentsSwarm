Scene Setup Snippets
Objects Creation and Manipulation
Note

The following scripts should only be run on the default new stage and only once. You can try these by creating a new stage via File > New and running from Window > Script Editor

Rigid Object Creation
The following snippet adds a dynamic cube with given properties and a ground plane to the scene.

import numpy as np
from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.api.objects.ground_plane import GroundPlane
from isaacsim.core.api.physics_context import PhysicsContext

PhysicsContext()
GroundPlane(prim_path="/World/groundPlane", size=10, color=np.array([0.5, 0.5, 0.5]))
DynamicCuboid(
    prim_path="/World/cube",
    position=np.array([-0.5, -0.2, 1.0]),
    scale=np.array([0.5, 0.5, 0.5]),
    color=np.array([0.2, 0.3, 0.0]),
)
View Objects
View classes in this extension are collections of similar prims. View classes manipulate the underlying objects in a vectorized way. Most View APIs require the world and the physics simulation to be initialized before they can be used. This can be achieved by adding the view class to the World’s scene and resetting the world as follows

from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.api.world import World
from isaacsim.core.prims import RigidPrim

# View classes are initialized when they are added to the scene and the world is reset
world = World()
cube = DynamicCuboid(prim_path="/World/cube_0")
rigid_prim = RigidPrim(prim_paths_expr="/World/cube_[0-100]")
world.scene.add(rigid_prim)
world.reset()
# rigid_prim is now initialized and can be used
which works when running the script via the Isaac Sim Python script. When using Window > Script Editor, to run the snippets you need to use the asynchronous version of reset as follows

import asyncio

from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.api.world import World
from isaacsim.core.prims import RigidPrim


async def init():
    if World.instance():
        World.instance().clear_instance()
    world = World()
    await world.initialize_simulation_context_async()
    world.scene.add_default_ground_plane(z_position=-1.0)
    cube = DynamicCuboid(prim_path="/World/cube_0")
    rigid_prim = RigidPrim(prim_paths_expr="/World/cube_[0-100]")
    # View classes are internally initialized when they are added to the scene and the world is reset
    world.scene.add(rigid_prim)
    await world.reset_async()
    # rigid_prim is now initialized and can be used


asyncio.ensure_future(init())
See Workflows tutorial for more details about various workflows for developing in Isaac Sim.

Create RigidPrim
The following snippet adds three cubes to the scene and creates a RigidPrim (formerly RigidPrimView) to manipulate the batch.

import asyncio

import numpy as np
from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.api.world import World
from isaacsim.core.prims import RigidPrim


async def example():
    if World.instance():
        World.instance().clear_instance()
    world = World()
    await world.initialize_simulation_context_async()
    world.scene.add_default_ground_plane(z_position=-1.0)

    # create rigid cubes
    for i in range(3):
        DynamicCuboid(prim_path=f"/World/cube_{i}")

    # create the view object to batch manipulate the cubes
    rigid_prim = RigidPrim(prim_paths_expr="/World/cube_[0-2]")
    world.scene.add(rigid_prim)
    await world.reset_async()
    # set world poses
    rigid_prim.set_world_poses(positions=np.array([[0, 0, 2], [0, -2, 2], [0, 2, 2]]))


asyncio.ensure_future(example())
See the API Documentation for all the possible operations supported by RigidPrim.

Create RigidContactView
There are scenarios where you are interested in net contact forces on each body and contact forces between specific bodies. This can be achieved via the RigidContactView object managed by the RigidPrim

import asyncio

import numpy as np
from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.api.world import World
from isaacsim.core.prims import RigidPrim


async def example():
    if World.instance():
        World.instance().clear_instance()
    world = World()
    await world.initialize_simulation_context_async()
    world.scene.add_default_ground_plane()

    # create three rigid cubes sitting on top of three others
    for i in range(3):
        DynamicCuboid(prim_path=f"/World/bottom_box_{i+1}", size=2, color=np.array([0.5, 0, 0]), mass=1.0)
        DynamicCuboid(prim_path=f"/World/top_box_{i+1}", size=2, color=np.array([0, 0, 0.5]), mass=1.0)

    # as before, create RigidContactView to manipulate bottom boxes but this time specify top boxes as filters to the view object
    # this allows receiving contact forces between the bottom boxes and top boxes
    bottom_box = RigidPrim(
        prim_paths_expr="/World/bottom_box_*",
        name="bottom_box",
        positions=np.array([[0, 0, 1.0], [-5.0, 0, 1.0], [5.0, 0, 1.0]]),
        contact_filter_prim_paths_expr=["/World/top_box_*"],
    )
    # create a RigidContactView to manipulate top boxes
    top_box = RigidPrim(
        prim_paths_expr="/World/top_box_*",
        name="top_box",
        positions=np.array([[0.0, 0, 3.0], [-5.0, 0, 3.0], [5.0, 0, 3.0]]),
        track_contact_forces=True,
    )

    world.scene.add(top_box)
    world.scene.add(bottom_box)
    await world.reset_async()

    # net contact forces acting on the bottom boxes
    print(bottom_box.get_net_contact_forces())
    # contact forces between the top and the bottom boxes
    print(bottom_box.get_contact_force_matrix())


asyncio.ensure_future(example())
More detailed information about the friction and contact forces can be obtained from the get_friction_data and get_contact_force_data respectively. These APIs provide all the contact forces and contact points between pairs of the sensor prims and filter prims. get_contact_force_data API provides the contact distances and contact normal vectors as well.

In the example below, we add three boxes to the scene and apply a tangential force of magnitude 10 to each. Then we use the aforementioned APIs to receive all the contact information and sum across all the contact points to find the friction/normal forces between the boxes and the ground plane.

import asyncio

import numpy as np
from isaacsim.core.api.materials.physics_material import PhysicsMaterial
from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.api.world import World
from isaacsim.core.prims import RigidPrim
from isaacsim.core.utils.stage import create_new_stage_async, update_stage_async


async def contact_force_example():
    g = 10
    await create_new_stage_async()
    if World.instance():
        World.instance().clear_instance()
    world = World()
    world.scene.add_default_ground_plane()
    await world.initialize_simulation_context_async()
    material = PhysicsMaterial(
        prim_path="/World/PhysicsMaterials",
        static_friction=0.5,
        dynamic_friction=0.5,
    )
    # create three rigid cubes sitting on top of three others
    for i in range(3):
        DynamicCuboid(
            prim_path=f"/World/Box_{i+1}", size=2, color=np.array([0, 0, 0.5]), mass=1.0
        ).apply_physics_material(material)

    # Creating RigidPrim with contact relevant keywords allows receiving contact information
    # In the following we indicate that we are interested in receiving up to 30 contact points data between the boxes and the ground plane
    box_view = RigidPrim(
        prim_paths_expr="/World/Box_*",
        positions=np.array([[0, 0, 1.0], [-5.0, 0, 1.0], [5.0, 0, 1.0]]),
        contact_filter_prim_paths_expr=["/World/defaultGroundPlane/GroundPlane/CollisionPlane"],
        max_contact_count=3 * 10,  # we don't expect more than 10 contact points for each box
    )

    world.scene.add(box_view)
    await world.reset_async()

    forces = np.array([[g, 0, 0], [g, 0, 0], [g, 0, 0]])
    box_view.apply_forces(forces)
    await update_stage_async()

    # tangential forces
    friction_forces, friction_points, friction_pair_contacts_count, friction_pair_contacts_start_indices = (
        box_view.get_friction_data(dt=1 / 60)
    )
    # normal forces
    forces, points, normals, distances, pair_contacts_count, pair_contacts_start_indices = (
        box_view.get_contact_force_data(dt=1 / 60)
    )
    # pair_contacts_count, pair_contacts_start_indices are tensors of size num_sensors x num_filters
    # friction_pair_contacts_count, friction_pair_contacts_start_indices are tensors of size num_sensors x num_filters
    # use the following tensors to sum across all the contact points
    force_aggregate = np.zeros((box_view._contact_view.num_shapes, box_view._contact_view.num_filters, 3))
    friction_force_aggregate = np.zeros((box_view._contact_view.num_shapes, box_view._contact_view.num_filters, 3))

    # process contacts for each pair i, j
    for i in range(pair_contacts_count.shape[0]):
        for j in range(pair_contacts_count.shape[1]):
            start_idx = pair_contacts_start_indices[i, j]
            friction_start_idx = friction_pair_contacts_start_indices[i, j]
            count = pair_contacts_count[i, j]
            friction_count = friction_pair_contacts_count[i, j]
            # sum/average across all the contact points for each pair
            pair_forces = forces[start_idx : start_idx + count]
            pair_normals = normals[start_idx : start_idx + count]
            force_aggregate[i, j] = np.sum(pair_forces * pair_normals, axis=0)

            # sum/average across all the friction pairs
            pair_forces = friction_forces[friction_start_idx : friction_start_idx + friction_count]
            friction_force_aggregate[i, j] = np.sum(pair_forces, axis=0)

    print("friction forces: \n", friction_force_aggregate)
    print("contact forces: \n", force_aggregate)
    # get_contact_force_matrix API is equivalent to the summation of the individual contact forces computed above
    print("contact force matrix: \n", box_view.get_contact_force_matrix(dt=1 / 60))
    # get_net_contact_forces API is the summation of the all forces
    # in the current example because all the potential contacts are captured by the choice of our filter prims (/World/defaultGroundPlane/GroundPlane/CollisionPlane)
    # the following is similar to the reduction of the contact force matrix above across the filters
    print("net contact force: \n", box_view.get_net_contact_forces(dt=1 / 60))


asyncio.ensure_future(contact_force_example())
See the API Documentation for more information about RigidContactView.

Set Mass Properties for a Mesh
The snippet below shows how to set the mass of a physics object. Density can also be specified as an alternative

import omni
from omni.physx.scripts import utils
from pxr import UsdPhysics

stage = omni.usd.get_context().get_stage()
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
# Get the prim
cube_prim = stage.GetPrimAtPath(path)
# Make it a rigid body
utils.setRigidBody(cube_prim, "convexHull", False)

mass_api = UsdPhysics.MassAPI.Apply(cube_prim)
mass_api.CreateMassAttr(10)
### Alternatively set the density
mass_api.CreateDensityAttr(1000)
Get Size of a Mesh
The snippet below shows how to get the size of a mesh.

import omni
from pxr import Gf, Usd, UsdGeom

stage = omni.usd.get_context().get_stage()
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cone")
# Get the prim
prim = stage.GetPrimAtPath(path)
# Get the size
bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])
bbox_cache.Clear()
prim_bbox = bbox_cache.ComputeWorldBound(prim)
prim_range = prim_bbox.ComputeAlignedRange()
prim_size = prim_range.GetSize()
print(prim_size)
Apply Semantic Data on Entire Stage
The snippet below shows how to programmatically apply semantic data on objects by iterating the entire stage.

import omni.usd
from isaacsim.core.utils.semantics import add_labels


def remove_prefix(name, prefix):
    if name.startswith(prefix):
        return name[len(prefix) :]
    return name


def remove_numerical_suffix(name):
    suffix = name.split("_")[-1]
    if suffix.isnumeric():
        return name[: -len(suffix) - 1]
    return name


def remove_underscores(name):
    return name.replace("_", "")


stage = omni.usd.get_context().get_stage()
for prim in stage.Traverse():
    if prim.GetTypeName() == "Mesh":
        label = str(prim.GetPrimPath()).split("/")[-1]
        label = remove_prefix(label, "SM_")
        label = remove_numerical_suffix(label)
        label = remove_underscores(label)
        add_labels(prim, labels=[label], instance_name="class")
Convert Asset to USD
The below script will convert a non-USD asset like OBJ/STL/FBX to USD. This is meant to be used inside the Script Editor. For running it as a Standalone Application, Check Python Environment.

import asyncio

import carb
import omni


async def convert_asset_to_usd(input_obj: str, output_usd: str):
    import omni.kit.asset_converter

    def progress_callback(progress, total_steps):
        pass

    converter_context = omni.kit.asset_converter.AssetConverterContext()
    # setup converter and flags
    # converter_context.ignore_material = False
    # converter_context.ignore_animation = False
    # converter_context.ignore_cameras = True
    # converter_context.single_mesh = True
    # converter_context.smooth_normals = True
    # converter_context.preview_surface = False
    # converter_context.support_point_instancer = False
    # converter_context.embed_mdl_in_usd = False
    # converter_context.use_meter_as_world_unit = True
    # converter_context.create_world_as_default_root_prim = False
    instance = omni.kit.asset_converter.get_instance()
    task = instance.create_converter_task(input_obj, output_usd, progress_callback, converter_context)
    success = await task.wait_until_finished()
    if not success:
        carb.log_error(task.get_status(), task.get_detailed_error())
    print("converting done")


asyncio.ensure_future(
    convert_asset_to_usd(
        "</path/to/mesh.obj>",
        "</path/to/mesh.usd>",
    )
)
The details about the optional import options in lines 13-23 can be found here.

Physics How-Tos
Create A Physics Scene
import omni
from pxr import Gf, Sdf, UsdPhysics

stage = omni.usd.get_context().get_stage()
# Add a physics scene prim to stage
scene = UsdPhysics.Scene.Define(stage, Sdf.Path("/World/physicsScene"))
# Set gravity vector
scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
scene.CreateGravityMagnitudeAttr().Set(981.0)
The following can be added to set specific settings, in this case use CPU physics and the TGS solver

from pxr import PhysxSchema

PhysxSchema.PhysxSceneAPI.Apply(stage.GetPrimAtPath("/World/physicsScene"))
physxSceneAPI = PhysxSchema.PhysxSceneAPI.Get(stage, "/World/physicsScene")
physxSceneAPI.CreateEnableCCDAttr(True)
physxSceneAPI.CreateEnableStabilizationAttr(True)
physxSceneAPI.CreateEnableGPUDynamicsAttr(False)
physxSceneAPI.CreateBroadphaseTypeAttr("MBP")
physxSceneAPI.CreateSolverTypeAttr("TGS")
Adding a ground plane to a stage can be done via the following code: It creates a Z up plane with a size of 100 cm at a Z coordinate of -100

import omni
from pxr import Gf, PhysicsSchemaTools

stage = omni.usd.get_context().get_stage()
PhysicsSchemaTools.addGroundPlane(stage, "/World/groundPlane", "Z", 100, Gf.Vec3f(0, 0, -100), Gf.Vec3f(1.0))
Enable Physics And Collision For a Mesh
The script below assumes there is a physics scene in the stage.

import omni
from omni.physx.scripts import utils

# Create a cube mesh in the stage
stage = omni.usd.get_context().get_stage()
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
# Get the prim
cube_prim = stage.GetPrimAtPath(path)
# Enable physics on prim
# If a tighter collision approximation is desired use convexDecomposition instead of convexHull
utils.setRigidBody(cube_prim, "convexHull", False)
If a tighter collision approximation is desired use convexDecomposition

import omni
from omni.physx.scripts import utils

# Create a cube mesh in the stage
stage = omni.usd.get_context().get_stage()
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
# Get the prim
cube_prim = stage.GetPrimAtPath(path)
# Enable physics on prim
# If a tighter collision approximation is desired use convexDecomposition instead of convexHull
utils.setRigidBody(cube_prim, "convexDecomposition", False)
To verify that collision meshes have been successfully enabled, click the “eye” icon > “Show By Type” > “Physics Mesh” > “All”. This will show the collision meshes as pink outlines on the objects.

Traverse a stage and assign collision meshes to children
import omni
from omni.physx.scripts import utils
from pxr import Gf, Usd, UsdGeom

stage = omni.usd.get_context().get_stage()


def add_cube(stage, path, size: float = 10, offset: Gf.Vec3d = Gf.Vec3d(0, 0, 0)):
    cubeGeom = UsdGeom.Cube.Define(stage, path)
    cubeGeom.CreateSizeAttr(size)
    cubeGeom.AddTranslateOp().Set(offset)


### The following prims are added for illustrative purposes
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Torus")
# all prims under AddCollision will get collisions assigned
add_cube(stage, "/World/Cube_0", offset=Gf.Vec3d(100, 100, 0))
# create a prim nested under without a parent
add_cube(stage, "/World/Nested/Cube", offset=Gf.Vec3d(100, 0, 100))
###

# Traverse all prims in the stage starting at this path
curr_prim = stage.GetPrimAtPath("/")

for prim in Usd.PrimRange(curr_prim):
    # only process shapes and meshes
    if (
        prim.IsA(UsdGeom.Cylinder)
        or prim.IsA(UsdGeom.Capsule)
        or prim.IsA(UsdGeom.Cone)
        or prim.IsA(UsdGeom.Sphere)
        or prim.IsA(UsdGeom.Cube)
    ):
        # use a ConvexHull for regular prims
        utils.setCollider(prim, approximationShape="convexHull")
    elif prim.IsA(UsdGeom.Mesh):
        # "None" will use the base triangle mesh if available
        # Can also use "convexDecomposition", "convexHull", "boundingSphere", "boundingCube"
        utils.setCollider(prim, approximationShape="None")
    pass
pass
Do Overlap Test
These snippets detect and report when objects overlap with a specified cubic/spherical region. The following is assumed: the stage contains a physics scene, all objects have collision meshes enabled, and the play button has been clicked.

The parameters: extent, origin and rotation (or origin and radius) define the cubic/spherical region to check overlap against. The output of the physX query is the number of objects that overlaps with this cubic/spherical region.

import carb
import omni
import omni.physx
from omni.physx import get_physx_scene_query_interface
from pxr import Gf, UsdGeom, Vt


def report_hit(hit):
    # When a collision is detected, the object color changes to red.
    hitColor = Vt.Vec3fArray([Gf.Vec3f(180.0 / 255.0, 16.0 / 255.0, 0.0)])
    usdGeom = UsdGeom.Mesh.Get(omni.usd.get_context().get_stage(), hit.rigid_body)
    usdGeom.GetDisplayColorAttr().Set(hitColor)
    return True


def check_overlap():
    # Defines a cubic region to check overlap with
    extent = carb.Float3(20.0, 20.0, 20.0)
    origin = carb.Float3(0.0, 0.0, 0.0)
    rotation = carb.Float4(0.0, 0.0, 1.0, 0.0)
    # physX query to detect number of hits for a cubic region
    numHits = get_physx_scene_query_interface().overlap_box(extent, origin, rotation, report_hit, False)
    # physX query to detect number of hits for a spherical region
    # numHits = get_physx_scene_query_interface().overlap_sphere(radius, origin, report_hit, False)
    return numHits > 0
Do Raycast Test
This snippet detects the closest object that intersects with a specified ray. The following is assumed: the stage contains a physics scene, all objects have collision meshes enabled, and the play button has been clicked.

The parameters: origin, rayDir and distance define a ray along which a ray hit might be detected. The output of the query can be used to access the object’s reference, and its distance from the raycast origin.

import carb
import omni
import omni.physx
from omni.physx import get_physx_scene_query_interface
from pxr import Gf, UsdGeom, Vt


def check_raycast():
    # Projects a raycast from 'origin', in the direction of 'rayDir', for a length of 'distance' cm
    # Parameters can be replaced with real-time position and orientation data  (e.g. of a camera)
    origin = carb.Float3(0.0, 0.0, 0.0)
    rayDir = carb.Float3(1.0, 0.0, 0.0)
    distance = 100.0
    # physX query to detect closest hit
    hit = get_physx_scene_query_interface().raycast_closest(origin, rayDir, distance)
    if hit["hit"]:
        # Change object color to yellow and record distance from origin
        usdGeom = UsdGeom.Mesh.Get(omni.usd.get_context().get_stage(), hit["rigidBody"])
        hitColor = Vt.Vec3fArray([Gf.Vec3f(255.0 / 255.0, 255.0 / 255.0, 0.0)])
        usdGeom.GetDisplayColorAttr().Set(hitColor)
        distance = hit["distance"]
        return usdGeom.GetPath().pathString, distance
    return None, 10000.0


print(check_raycast())
USD How-Tos
Creating, Modifying, Assigning Materials
import omni
from pxr import Gf, Sdf, UsdShade

mtl_created_list = []
# Create a new material using OmniGlass.mdl
omni.kit.commands.execute(
    "CreateAndBindMdlMaterialFromLibrary",
    mdl_name="OmniGlass.mdl",
    mtl_name="OmniGlass",
    mtl_created_list=mtl_created_list,
)
# Get reference to created material
stage = omni.usd.get_context().get_stage()
mtl_prim = stage.GetPrimAtPath(mtl_created_list[0])
# Set material inputs, these can be determined by looking at the .mdl file
# or by selecting the Shader attached to the Material in the stage window and looking at the details panel
omni.usd.create_material_input(mtl_prim, "glass_color", Gf.Vec3f(0, 1, 0), Sdf.ValueTypeNames.Color3f)
omni.usd.create_material_input(mtl_prim, "glass_ior", 1.0, Sdf.ValueTypeNames.Float)
# Create a prim to apply the material to
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
# Get the path to the prim
cube_prim = stage.GetPrimAtPath(path)
# Bind the material to the prim
cube_mat_shade = UsdShade.Material(mtl_prim)
UsdShade.MaterialBindingAPI(cube_prim).Bind(cube_mat_shade, UsdShade.Tokens.strongerThanDescendants)
Assigning a texture to a material that supports it can be done as follows:

import carb
import omni
from pxr import Sdf, UsdShade

# Change the server to your Nucleus install, default is set to localhost in omni.isaac.sim.base.kit
default_server = carb.settings.get_settings().get("/persistent/isaac/asset_root/default")
mtl_created_list = []
# Create a new material using OmniPBR.mdl
omni.kit.commands.execute(
    "CreateAndBindMdlMaterialFromLibrary",
    mdl_name="OmniPBR.mdl",
    mtl_name="OmniPBR",
    mtl_created_list=mtl_created_list,
)
stage = omni.usd.get_context().get_stage()
mtl_prim = stage.GetPrimAtPath(mtl_created_list[0])
# Set material inputs, these can be determined by looking at the .mdl file
# or by selecting the Shader attached to the Material in the stage window and looking at the details panel
omni.usd.create_material_input(
    mtl_prim,
    "diffuse_texture",
    default_server + "/Isaac/Samples/DR/Materials/Textures/marble_tile.png",
    Sdf.ValueTypeNames.Asset,
)
# Create a prim to apply the material to
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
# Get the path to the prim
cube_prim = stage.GetPrimAtPath(path)
# Bind the material to the prim
cube_mat_shade = UsdShade.Material(mtl_prim)
UsdShade.MaterialBindingAPI(cube_prim).Bind(cube_mat_shade, UsdShade.Tokens.strongerThanDescendants)
Adding a transform matrix to a prim
import omni
from pxr import Gf, UsdGeom

# Create a cube mesh in the stage
stage = omni.usd.get_context().get_stage()
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
# Get the prim and set its transform matrix
cube_prim = stage.GetPrimAtPath("/World/Cube")
xform = UsdGeom.Xformable(cube_prim)
transform = xform.AddTransformOp()
mat = Gf.Matrix4d()
mat.SetTranslateOnly(Gf.Vec3d(0.10, 1, 1.5))
mat.SetRotateOnly(Gf.Rotation(Gf.Vec3d(0, 1, 0), 290))
transform.Set(mat)
Align two USD prims
import omni
from pxr import Gf, UsdGeom

stage = omni.usd.get_context().get_stage()
# Create a cube
result, path_a = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
prim_a = stage.GetPrimAtPath(path_a)
# change the cube pose
xform = UsdGeom.Xformable(prim_a)
transform = xform.AddTransformOp()
mat = Gf.Matrix4d()
mat.SetTranslateOnly(Gf.Vec3d(0.10, 1, 1.5))
mat.SetRotateOnly(Gf.Rotation(Gf.Vec3d(0, 1, 0), 290))
transform.Set(mat)
# Create a second cube
result, path_b = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
prim_b = stage.GetPrimAtPath(path_b)
# Get the transform of the first cube
pose = omni.usd.utils.get_world_transform_matrix(prim_a)
# Clear the transform on the second cube
xform = UsdGeom.Xformable(prim_b)
xform.ClearXformOpOrder()
# Set the pose of prim_b to that of prim_b
xform_op = xform.AddXformOp(UsdGeom.XformOp.TypeTransform, UsdGeom.XformOp.PrecisionDouble, "")
xform_op.Set(pose)
Get World Transform At Current Timestamp For Selected Prims
import omni
from pxr import Gf, UsdGeom

usd_context = omni.usd.get_context()
stage = usd_context.get_stage()

#### For testing purposes we create and select a prim
#### This section can be removed if you already have a prim selected
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
cube_prim = stage.GetPrimAtPath(path)
# change the cube pose
xform = UsdGeom.Xformable(cube_prim)
transform = xform.AddTransformOp()
mat = Gf.Matrix4d()
mat.SetTranslateOnly(Gf.Vec3d(0.10, 1, 1.5))
mat.SetRotateOnly(Gf.Rotation(Gf.Vec3d(0, 1, 0), 290))
transform.Set(mat)
omni.usd.get_context().get_selection().set_prim_path_selected(path, True, True, True, False)
####

# Get list of selected primitives
selected_prims = usd_context.get_selection().get_selected_prim_paths()
# Get the current timecode
timeline = omni.timeline.get_timeline_interface()
timecode = timeline.get_current_time() * timeline.get_time_codes_per_seconds()
# Loop through all prims and print their transforms
for s in selected_prims:
    curr_prim = stage.GetPrimAtPath(s)
    print("Selected", s)
    pose = omni.usd.utils.get_world_transform_matrix(curr_prim, timecode)
    print("Matrix Form:", pose)
    print("Translation: ", pose.ExtractTranslation())
    q = pose.ExtractRotation().GetQuaternion()
    print("Rotation: ", q.GetReal(), ",", q.GetImaginary()[0], ",", q.GetImaginary()[1], ",", q.GetImaginary()[2])
Save current stage to USD
This can be useful if generating a stage in Python and you want to store it to reload later to debugging

import carb
import omni

# Create a prim
result, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Cube")
# Change the path as needed
omni.usd.get_context().save_as_stage("/path/to/asset/saved.usd", None)