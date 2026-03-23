ROS2 Simulation Control
Learning Objectives
In this page, you will learn how to:

Understand the ROS 2 Simulation Control extension for Isaac Sim

Control Isaac Sim simulations using ROS 2 services and actions

Manipulate simulation entities and worlds using ROS 2 interfaces

Step through simulations programmatically

Getting Started
Prerequisite

Complete ROS 2 Installation (Default).

If using multiple systems, set the FASTRTPS_DEFAULT_PROFILES_FILE environment variable as per instructions in ROS 2 Installation (Default) before launching Isaac Sim, as well as any terminal where ROS messages will be sent or received, and ROS2 Extension is enabled.

Isaac Sim 5.0 or later

ROS 2 (Humble or later)

Install Simulation Interfaces package using:


Humble
sudo apt install ros-humble-simulation-interfaces

Jazzy
For reference, see the source code for the Simulation Interfaces package here.

Overview
The ROS 2 Simulation Control extension uses the ROS 2 Simulation Interfaces to control Isaac Sim functions. This extension is designed to be scalable, allowing multiple services and actions to run simultaneously with little performance overhead.

The extension provides comprehensive control over Isaac Sim through ROS 2 services and actions, including:

Simulation State Control: Play, pause, stop, and step through simulations

Entity Management: Spawn, delete, and manipulate simulation entities (prims)

World Management: Load, unload, and query simulation worlds (USD files)

State Querying: Get information about entities, simulation state, and available resources

This allows you to control Isaac Sim programmatically or through the ROS 2 command line interface using the Simulation Interfaces package to enable workflows like automated testing. This page lists and provides example commands for all of the services and actions from Simulation Interfaces supported by Isaac Sim.

Enabling the Extension
Enable Automatically
Open Isaac Sim from the terminal with the following command:

./isaac-sim.sh --/isaac/startup/ros_sim_control_extension=True
Enable Manually
Open Isaac Sim

Enable the extension from the Extension Manager: isaacsim.ros2.sim_control

Available Services and Actions
The extension provides the following ROS 2 services:

/get_simulator_features: Lists the supported features in this Isaac Sim implementation

/set_simulation_state: Set simulation to specific state (stopped/playing/paused/quitting)

/get_simulation_state: Get current simulation state

/get_entities: Get list of all entities (prims) in the simulation

/get_entity_info: Get detailed information about a specific entity (currently returns OBJECT category type)

/get_entity_state: Get the pose, twist, and acceleration of a specific entity

/get_entities_states: Get the states (pose, twist, acceleration) of multiple entities with filtering

/delete_entity: Delete a specific entity (prim) from the simulation

/spawn_entity: Spawn a new entity into the simulation at a specified location

/reset_simulation: Reset the simulation environment to its initial state

/set_entity_state: Sets the state (pose, twist) of a specific entity in the simulation

/step_simulation: Step the simulation forward by a specific number of frames

/load_world: Load a world or environment file into the simulation

/unload_world: Unload the current world and create an empty stage

/get_current_world: Get information about the currently loaded world

/get_available_worlds: Get a list of available world files that can be loaded

And the following ROS 2 actions:

/simulate_steps: Action for stepping the simulation with progress feedback

Using the ROS 2 Simulation Control Services
This section describes how to use each of the available services in detail.

GetSimulatorFeatures Service
The GetSimulatorFeatures service lists the subset of services and actions supported by Isaac Sim from simulation_interfaces.

ros2 service call /get_simulator_features simulation_interfaces/srv/GetSimulatorFeatures
Notes:

Returns a list of supported features (for example, SPAWNING, DELETING, ENTITY_STATE_GETTING)

Reports USD file format support using the spawn_formats field

Provides custom_info with details about the implementation

See the full list of simulator features

SetSimulationState Service
The SetSimulationState service updates the global state of the simulation (stopped/playing/paused/quitting) corresponding to enums defined in SimulationState.msg (STATE_STOPPED, STATE_PLAYING, STATE_PAUSED, STATE_QUITTING).

To set simulation state to playing:

ros2 service call /set_simulation_state simulation_interfaces/srv/SetSimulationState "{state: {state: 1}}"  # 1=playing
To set simulation state to paused:

ros2 service call /set_simulation_state simulation_interfaces/srv/SetSimulationState "{state: {state: 2}}"  # 2=paused
To set simulation state to stopped:

ros2 service call /set_simulation_state simulation_interfaces/srv/SetSimulationState "{state: {state: 0}}"  # 0=stopped
To quit the simulator:

ros2 service call /set_simulation_state simulation_interfaces/srv/SetSimulationState "{state: {state: 3}}"  # 3=quit
Notes:

State 0 (Stopped) is equivalent to pausing and resetting the simulation

State 1 (Playing) starts the simulation timeline

State 2 (Paused) pauses the simulation at the current time

State 3 (Quitting) shuts down Isaac Sim

GetSimulationState Service
The GetSimulationState service retrieves the current state of the entire simulation (stopped/playing/paused/quitting) corresponding to enums defined in SimulationState.msg (STATE_STOPPED, STATE_PLAYING, STATE_PAUSED, STATE_QUITTING).

ros2 service call /get_simulation_state simulation_interfaces/srv/GetSimulationState
Notes:

Returns state 0 for stopped, 1 for playing, 2 for paused

Used to query the simulation state before performing operations like stepping

GetEntities Service
The GetEntities service retrieves a list of all entities present in the simulation with optional filtering (using regex pattern).

Get all entities in the simulation:

ros2 service call /get_entities simulation_interfaces/srv/GetEntities "{filters: {filter: ''}}"
Get entities with full paths or partial paths. In this case filter for prims containing ‘camera’ in the path:

ros2 service call /get_entities simulation_interfaces/srv/GetEntities "{filters: {filter: 'camera'}}"
Get entities with paths starting with ‘/World’:

ros2 service call /get_entities simulation_interfaces/srv/GetEntities "{filters: {filter: '^/World'}}"
Get entities with paths ending with ‘mesh’:

ros2 service call /get_entities simulation_interfaces/srv/GetEntities "{filters: {filter: 'mesh$'}}"
Notes:

The filter parameter accepts POSIX Extended regular expressions for matching entity names (prim paths)

Isaac Sim uses the full USD prim paths as entity names

GetEntityInfo Service
The GetEntityInfo service provides detailed information about a specific entity, such as its type and properties.

ros2 service call /get_entity_info simulation_interfaces/srv/GetEntityInfo "{entity: '/World/robot'}"
Notes:

Returns RESULT_OK with EntityInfo if the entity exists

Returns RESULT_OPERATION_FAILED if the entity doesn’t exist

The EntityInfo contains: * category: Currently always set to OBJECT (EntityCategory.OBJECT) * description: Empty string (reserved for future use) * tags: Empty array (reserved for future use)

GetEntityState Service
The GetEntityState service gets the pose, twist, acceleration of a specific entity relative to a given reference frame. Currently only world frames are supported.

ros2 service call /get_entity_state simulation_interfaces/srv/GetEntityState "{entity: '/World/robot'}"
Notes:

For entities with RigidBodyAPI, both pose and velocities will be returned

For entities without RigidBodyAPI, only pose will be returned with zero velocities

Acceleration values are always reported as zero (not provided by the current API)

Returns RESULT_OK if successfully retrieved entity state

Returns RESULT_NOT_FOUND if entity does not exist

Returns RESULT_OPERATION_FAILED if error retrieving entity state

GetEntitiesStates Service
The GetEntitiesStates service fetches the states (pose, twist, acceleration) in the world frame of multiple entities in the simulation.

Get states for all entities in the simulation:

ros2 service call /get_entities_states simulation_interfaces/srv/GetEntitiesStates "{filters: {filter: ''}}"
Get states for entities containing ‘robot’ in their path:

ros2 service call /get_entities_states simulation_interfaces/srv/GetEntitiesStates "{filters: {filter: 'robot'}}"
Get states for entities with paths starting with ‘/World’:

ros2 service call /get_entities_states simulation_interfaces/srv/GetEntitiesStates "{filters: {filter: '^/World'}}"
Notes:

Combines functionality from GetEntities and GetEntityState services

Filters entities first using regex pattern matching

Retrieves state for each filtered entity

Returns list of entity paths and corresponding states

For entities with RigidBodyAPI, both pose and velocities will be returned

For entities without RigidBodyAPI, only pose will be returned with zero velocities

Acceleration values are always reported as zero (not provided by the current API)

Using this service is more efficient than making multiple GetEntityState calls when you need states for many entities

Returns RESULT_OK if successfully retrieved entity states

Returns RESULT_OPERATION_FAILED if error in filtering or retrieving states

DeleteEntity Service
The DeleteEntity service deletes a specified entity in the simulation.

ros2 service call /delete_entity simulation_interfaces/srv/DeleteEntity "{entity: '/World/robot'}"
Notes:

The service will return RESULT_OK if the entity was successfully deleted

Returns RESULT_OPERATION_FAILED if the entity is protected and cannot be deleted

Uses prim_utils.is_prim_no_delete() to check if a prim can be deleted before attempting deletion

SpawnEntity Service
The SpawnEntity service spawns a new entity into the simulation at a specified location.

Basic entity spawn with default position:

ros2 service call /spawn_entity simulation_interfaces/srv/SpawnEntity "{name: 'MyEntity', allow_renaming: false, uri: '/path/to/model.usd'}"
Spawn with specific position and orientation:

ros2 service call /spawn_entity simulation_interfaces/srv/SpawnEntity "{name: 'PositionedEntity', allow_renaming: false, uri: '/path/to/model.usd', initial_pose: {pose: {position: {x: 1.0, y: 2.0, z: 3.0}, orientation: {w: 1.0, x: 0.0, y: 0.0, z: 0.0}}}}"
Empty Xform creation (no URI):

ros2 service call /spawn_entity simulation_interfaces/srv/SpawnEntity "{name: 'EmptyXform', allow_renaming: false, uri: ''}"
With auto-renaming enabled:

ros2 service call /spawn_entity simulation_interfaces/srv/SpawnEntity "{name: 'AutoRenamedEntity', allow_renaming: true, uri: '/path/to/model.usd'}"
With namespace specified:

ros2 service call /spawn_entity simulation_interfaces/srv/SpawnEntity "{name: 'NamespacedEntity', allow_renaming: false, uri: '/path/to/model.usd', entity_namespace: 'robot1'}"
Notes:

If URI is provided, loads the USD file as a reference in the given prim path

If URI is not provided, creates a Xform at the given prim path

All spawned prims are marked with a simulationInterfacesSpawned attribute for tracking

Returns RESULT_OK if the entity was successfully spawned

Returns NAME_NOT_UNIQUE (101) if the entity name already exists and allow_renaming is false

Returns NAME_INVALID (102) if the entity name is empty and allow_renaming is false

Returns RESOURCE_PARSE_ERROR (106) if failed to parse or load USD file

ResetSimulation Service
The ResetSimulation service resets the simulation environment to its initial state.

ros2 service call /reset_simulation simulation_interfaces/srv/ResetSimulation
Notes:

Stops the simulation timeline

Finds and removes all prims with simulationInterfacesSpawned attribute

Uses multiple passes to ensure all spawned entities are removed

Restarts the simulation timeline

Returns RESULT_OK if successfully reset

Returns RESULT_OPERATION_FAILED if error resetting simulation

SetEntityState Service
The SetEntityState service sets the state (pose, twist) of a specific entity in the simulation. Only transforms in the world frame are currently accepted.

Set only position and orientation:

ros2 service call /set_entity_state simulation_interfaces/srv/SetEntityState "{
  entity: '/World/Cube',
  state: {
    header: {frame_id: 'world'},
    pose: {
      position: {x: 1.0, y: 2.0, z: 3.0},
      orientation: {w: 1.0, x: 0.0, y: 0.0, z: 0.0}
    },
    twist: {
      linear: {x: 0.0, y: 0.0, z: 0.0},
      angular: {x: 0.0, y: 0.0, z: 0.0}
    }
  }
}"
Set position, orientation and velocity (for entities with rigid body physics):

ros2 service call /set_entity_state simulation_interfaces/srv/SetEntityState "{
  entity: '/World/RigidBody',
  state: {
    header: {frame_id: 'world'},
    pose: {
      position: {x: 1.0, y: 2.0, z: 3.0},
      orientation: {w: 1.0, x: 0.0, y: 0.0, z: 0.0}
    },
    twist: {
      linear: {x: 0.5, y: 0.0, z: 0.0},
      angular: {x: 0.0, y: 0.0, z: 0.1}
    }
  }
}"
Notes:

The position and orientation are always updated for any entity

Velocities are only set for entities with a RigidBodyAPI

For non-rigid bodies, only position and orientation will be set (velocity settings are ignored)

Acceleration settings are not currently supported and will be ignored

Returns RESULT_OK if successfully set entity state

Returns RESULT_NOT_FOUND if entity does not exist

Returns RESULT_OPERATION_FAILED if error setting entity state

StepSimulation Service
The StepSimulation service simulates a finite number of steps and returns to PAUSED state.

Step the simulation by 1 frame (note: will use 2 steps internally):

ros2 service call /step_simulation simulation_interfaces/srv/StepSimulation "{steps: 1}"
Step the simulation by 10 frames:

ros2 service call /step_simulation simulation_interfaces/srv/StepSimulation "{steps: 10}"
Step the simulation by 100 frames:

ros2 service call /step_simulation simulation_interfaces/srv/StepSimulation "{steps: 100}"
Notes:

The simulation must be in a paused state before stepping can be performed

The service call will block until all steps are completed

After stepping completes, the simulation will automatically return to a paused state

Returns RESULT_OK if stepping completed successfully

Returns RESULT_INCORRECT_STATE if the simulation is not paused when the service is called

Returns RESULT_OPERATION_FAILED if any error occurs during stepping

LoadWorld Service
The LoadWorld service loads a world or environment file into the simulation, clearing the current scene and setting the simulation to stopped state. Currently supports USD format worlds.

Load a world from a USD file:

ros2 service call /load_world simulation_interfaces/srv/LoadWorld "{uri: '/path/to/world.usd'}"
Load a sample world with Isaac Sim sample environments:

ros2 service call /load_world simulation_interfaces/srv/LoadWorld "{uri: 'https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/Environments/Simple_Room/simple_room.usd'}"
Load a sample world with a ROS2 scenario:

ros2 service call /load_world simulation_interfaces/srv/LoadWorld "{uri: 'https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/Samples/ROS2/Scenario/carter_warehouse_apriltags_worker.usd'}"
Notes:

Only USD files (.usd, .usda, .usdc, .usdz) are supported

The simulation must be stopped or paused before loading a world (not playing)

Loading a world will clear the current scene and create a new stage from the USD file

If the given path cannot be found directly, Isaac Sim will automatically try prefixing it with the default asset root path

Returns RESULT_OK if the world was successfully loaded

Returns UNSUPPORTED_FORMAT if the file format is not supported

Returns RESOURCE_PARSE_ERROR if the USD file cannot be parsed or loaded

Returns RESULT_OPERATION_FAILED if the simulation is playing when the service is called

UnloadWorld Service
The UnloadWorld service unloads the current world from the simulation, clearing the current scene and creating a new empty stage. Any previously spawned entities will be removed.

ros2 service call /unload_world simulation_interfaces/srv/UnloadWorld
Notes:

The simulation must be stopped or paused before unloading a world (not playing)

Creates a new empty stage after unloading the current world

Returns RESULT_OK if the world was successfully unloaded

Returns NO_WORLD_LOADED if no world is currently loaded

Returns RESULT_OPERATION_FAILED if the simulation is playing when the service is called

GetCurrentWorld Service
The GetCurrentWorld service returns information about the currently loaded world, including its URI, name, and format.

ros2 service call /get_current_world simulation_interfaces/srv/GetCurrentWorld
Notes:

Returns world information including URI and name if a world is loaded from a file

For worlds created in memory (new stage), returns empty URI and “untitled_world” as the name

Returns RESULT_OK with world information if successful

Returns NO_WORLD_LOADED if no world is currently loaded

GetAvailableWorlds Service
The GetAvailableWorlds service returns a list of available world files that can be loaded into the simulation. It searches default Isaac Sim paths for USD world files, with support for TagsFilter-based filtering.

Get all default available worlds:

ros2 service call /get_available_worlds simulation_interfaces/srv/GetAvailableWorlds
Get worlds with tag filtering (search for default worlds with specific tags in filename):

ros2 service call /get_available_worlds simulation_interfaces/srv/GetAvailableWorlds "{filter: {tags: ['warehouse', 'carter']}, continue_on_error: true}"
Search additional custom paths:

ros2 service call /get_available_worlds simulation_interfaces/srv/GetAvailableWorlds "{additional_sources: ['/custom/worlds/path'], continue_on_error: true}"
Offline-only search with additional local sources:

ros2 service call /get_available_worlds simulation_interfaces/srv/GetAvailableWorlds "{additional_sources: ['/home/user/custom_worlds', '/opt/isaac_worlds'], offline_only: true, continue_on_error: true}"
Notes:

Searches default Isaac Sim paths: /Isaac/Environments and /Isaac/Samples/ROS2/Scenario

Supports TagsFilter with FILTER_MODE_ANY (default) or FILTER_MODE_ALL for tag matching

Can search additional custom paths specified in additional_sources

Set offline_only: true to only search local filesystem paths

Set continue_on_error: true to continue searching even if some paths fail

Returns RESULT_OK with list of available worlds

Returns DEFAULT_SOURCES_FAILED if default asset paths are not accessible and no additional sources are provided

Using the ROS 2 Simulation Control Actions
SimulateSteps Action
The SimulateSteps action simulates a finite number of steps and returns to PAUSED state with feedback after each step.

Basic usage - Step the simulation by 10 frames:

ros2 action send_goal /simulate_steps simulation_interfaces/action/SimulateSteps "{steps: 10}"
With feedback - Step the simulation by 20 frames and show feedback:

ros2 action send_goal /simulate_steps simulation_interfaces/action/SimulateSteps "{steps: 20}" --feedback
Notes:

The simulation must be in a paused state before stepping can be performed

After steps are completed, the simulation will return to a paused state

You will receive feedback after each step showing completed and remaining steps

The action can be canceled while executing

Technical Details
The extension uses the omni.timeline interface to control the simulation state and provides a clean ROS 2 interface through standard services. The implementation includes:

A singleton ROS2ServiceManager to handle all ROS 2 services through a single node

A SimulationControl class that interfaces with Isaac Sim’s timeline

Thread-safe implementation for ROS 2 spinning independent of Action Graph interface

Extending
To add more simulation control services, extend the SimulationControl class and register additional services with the ROS2ServiceManager.

Summary
This page covered:

The ROS 2 Simulation Control extension and its capabilities

How to enable the extension in Isaac Sim

Using ROS 2 services to control simulation state (play, pause, stop)

Manipulating entities in the simulation (spawn, delete, get/set state, get info)

Managing simulation worlds (load, unload, query available worlds)

Using ROS 2 actions for simulation stepping with feedback

Technical implementation details of the extension