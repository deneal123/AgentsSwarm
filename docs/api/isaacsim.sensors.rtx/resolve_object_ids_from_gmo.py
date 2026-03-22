# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from isaacsim import SimulationApp

# Specify --/rtx-transient/stableIds/enabled=true to enable StableIdMap output
simulation_app = SimulationApp(
    {"headless": True, "enable_motion_bvh": True, "extra_args": ["--/rtx-transient/stableIds/enabled=true"]}
)

import carb
import omni.timeline
from isaacsim.core.utils.stage import open_stage
from isaacsim.sensors.rtx import LidarRtx, get_gmo_data
from isaacsim.storage.native import get_assets_root_path

assets_root_path = get_assets_root_path()
if assets_root_path is None:
    carb.log_error("Could not find Isaac Sim assets folder")
    simulation_app.close()
    sys.exit()

# Load simple warehouse scene
open_stage(assets_root_path + "/Isaac/Environments/Simple_Warehouse/warehouse_with_forklifts.usd")

additional_lidar_attributes = {
    "omni:sensor:Core:auxOutputType": "FULL",
}

my_lidar = LidarRtx(
    prim_path="/World/lidar",
    name="lidar",
    position=(0, 0, 1.5),
    **additional_lidar_attributes,
)
my_lidar.initialize()
my_lidar.attach_annotator("GenericModelOutput")
my_lidar.attach_annotator("StableIdMap")

i = 0
timeline = omni.timeline.get_timeline_interface()
timeline.play()

# Wait for the lidar to be ready
for _ in range(3):
    simulation_app.update()

# Step one frame to get the lidar data
simulation_app.update()

# Convert the StableIdMap buffer to a dictionary of stable IDs to labels
stable_id_map_buffer = my_lidar.get_current_frame()["StableIdMap"]
stable_id_map = LidarRtx.decode_stable_id_mapping(stable_id_map_buffer.tobytes())

# Get the object IDs from the GenericModelOutput buffer
gmo_buffer = my_lidar.get_current_frame()["GenericModelOutput"]
gmo_data = get_gmo_data(gmo_buffer)
obj_ids = LidarRtx.get_object_ids(gmo_data.objId)

# Print the object IDs and their labels
for obj_id in set(obj_ids):
    if obj_id in stable_id_map:
        carb.log_warn(f"Object ID {obj_id} found in stable ID map: {stable_id_map[obj_id]}")

timeline.stop()
simulation_app.close()
