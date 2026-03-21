Core API Overview
Important

Isaac Sim 5.0.0 has introduced the Core Experimental API: a rewritten implementation of the current Core API designed to be more robust, flexible, and powerful, yet still maintain the core utilities and wrapper concepts.

Going forward, it will become the base API used in all Isaac Sim source code. The current Core API will be deprecated and removed in future releases.

Therefore, we strongly encourage early adoption and use of the Core Experimental API.

Core API is a Wrapper
Isaac Sim Core API are wrappers for raw USD and physics engine APIs, tailored to suit robotics applications. Here is adding a cube and apply physics properties to it using the raw USD

import omni
from pxr import Gf, PhysicsSchemaTools, PhysxSchema, UsdGeom, UsdPhysics

stage = omni.usd.get_context().get_stage()

# Setting up Physics Scene
gravity = 9.8
scene = UsdPhysics.Scene.Define(stage, "/World/physics")
scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
scene.CreateGravityMagnitudeAttr().Set(gravity)
PhysxSchema.PhysxSceneAPI.Apply(stage.GetPrimAtPath("/World/physics"))
physxSceneAPI = PhysxSchema.PhysxSceneAPI.Get(stage, "/World/physics")
physxSceneAPI.CreateEnableCCDAttr(True)
physxSceneAPI.CreateEnableStabilizationAttr(True)
physxSceneAPI.CreateEnableGPUDynamicsAttr(False)
physxSceneAPI.CreateBroadphaseTypeAttr("MBP")
physxSceneAPI.CreateSolverTypeAttr("TGS")

# Setting up Ground Plane
PhysicsSchemaTools.addGroundPlane(stage, "/World/groundPlane", "Z", 15, Gf.Vec3f(0, 0, 0), Gf.Vec3f(0.7))

# Adding a Cube
path = "/World/Cube"
cubeGeom = UsdGeom.Cube.Define(stage, path)
cubePrim = stage.GetPrimAtPath(path)
size = 0.5
offset = Gf.Vec3f(0.5, 0.2, 1.0)
cubeGeom.CreateSizeAttr(size)
cubeGeom.AddTranslateOp().Set(offset)

# Attach Rigid Body and Collision Preset
rigid_api = UsdPhysics.RigidBodyAPI.Apply(cubePrim)
rigid_api.CreateRigidBodyEnabledAttr(True)
UsdPhysics.CollisionAPI.Apply(cubePrim)
Here is adding a cube with physics and material properties to stage using Core API.

import numpy as np
from isaacsim.core.api.objects import DynamicCuboid

DynamicCuboid(
    prim_path="/new_cube_2",
    name="cube_1",
    position=np.array([0, 0, 1.0]),
    scale=np.array([0.6, 0.5, 0.2]),
    size=1.0,
    color=np.array([255, 0, 0]),
)
Application vs Simulation vs World vs Scene vs Stage
../_images/WorldSceneStage.png
Everything in USD is a primitive (prim) with attributes.

A Simulation (the sim) moves these prims forward through time by literally changing these attributes programmatically.

The Application is the thing that manages the gross aspects of the simulation (how things are rendered, for example) and how the user interacts with it. If there is a GUI for the sim, it is a part of the application.

A Stage is a USD concept, and defines the logical and relational context for prims in the simulation. If a mug prim is on a table prim then that relationship is expressed by the relative locations of those prims on the stage, and the specific attributes each has. In this way, the stage provides context for the application: prims cannot exist without a stage and so an application concerned with prims requires a stage to function.

Similarly, the World is what provides context to the simulation, defining which prims are relevant to the ongoing flow of time, the scene, and managing the aspects of the simulation that are most important to the user.

For example, imagine you are going to see a play at a theater. The theater is like the application, your gateway to the play, while the simulation is the play itself, defined by a program. You take your seat and you can see the stage, where the play will take place. When the play starts, the curtain rises and reveals a scene composed props and actors that then act out that part of the play. When it’s time to move to the next scene, the curtain falls, the scene is reset, and then the curtain rises again, revealing the next part of the play. The stage crew and all the mechanical devices behind the scene that manages the curtain and the props is the world of the play.