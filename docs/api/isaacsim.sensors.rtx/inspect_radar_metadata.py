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


import argparse

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True, "enable_motion_bvh": True})

import omni
import omni.replicator.core as rep
from isaacsim.core.utils.stage import is_stage_loading, open_stage
from isaacsim.sensors.rtx import get_gmo_data
from isaacsim.storage.native import get_assets_root_path
from pxr import Gf

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--test", default=False, action="store_true", help="Run in test mode")
args, unknown = parser.parse_known_args()

# Load the small warehouse scene
assets_root_path = get_assets_root_path()
open_stage(usd_path=assets_root_path + "/Isaac/Environments/Simple_Warehouse/warehouse.usd")
while is_stage_loading():
    simulation_app.update()

# Place a basic radar in the scene, overriding attributes as necessary
# Specify attributes to apply to the ``OmniRadar`` prim.
custom_attributes = {"omni:sensor:WpmDmat:auxOutputType": "FULL"}
_, radar = omni.kit.commands.execute(
    "IsaacSensorCreateRtxRadar",
    translation=Gf.Vec3d(0, 0, 1),
    orientation=Gf.Quatd(1, 0, 0, 0),
    path="/radar",
    parent=None,
    visibility=False,
    variant=None,
    force_camera_prim=False,
    **custom_attributes,
)
# Initialize the radar and attach an annotator
ANNOTATOR_NAME = "GenericModelOutput"
# Create a render product for the sensor.
render_product = rep.create.render_product(radar.GetPath(), resolution=(1024, 1024))
# Attach an annotator to the render product
annotator = rep.AnnotatorRegistry.get_annotator("GenericModelOutput")
annotator.attach([render_product.path])


GMO_FIELDS = [
    "numElements",
    "x",
    "y",
    "z",
    "scalar",
    "sensorID",
    "scanIdx",
    "cycleCnt",
    "maxRangeM",
    "minVelMps",
    "maxVelMps",
    "minAzRad",
    "maxAzRad",
    "minElRad",
    "maxElRad",
    "rv_ms",
]


# Run for a few frames, inspecting the data at each step
def inspect_radar_metadata(frame: int, gmo_buffer: dict) -> None:
    # Read GenericModelOutput struct from buffer
    gmo = get_gmo_data(gmo_buffer)
    # Print some useful information
    print(f"Frame {frame}")
    for field in GMO_FIELDS:
        print(f"-- {field}: {getattr(gmo, field)}")
    return


timeline = omni.timeline.get_timeline_interface()
timeline.play()
i = 0
# Run for 10 frames in test mode
while simulation_app.is_running() and (not args.test or i < 5):
    simulation_app.update()
    data = annotator.get_data()
    if len(data) > 0:
        inspect_radar_metadata(frame=i, gmo_buffer=data)
    i += 1
timeline.stop()

simulation_app.close()
