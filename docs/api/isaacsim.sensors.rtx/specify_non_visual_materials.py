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

simulation_app = SimulationApp({"headless": False})

import numpy as np
import omni.kit.commands
from isaacsim.core.api.materials import OmniPBR
from isaacsim.core.api.objects import VisualCuboid
from isaacsim.sensors.rtx import apply_nonvisual_material

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--test", default=False, action="store_true", help="Run in test mode")
args, unknown = parser.parse_known_args()

# Define cube positions, scales, and materials
cube_positions = [
    np.array([1, 1, 2]),
    np.array([1, 1, -2]),
    np.array([-1, 1, -2]),
    np.array([-1, -3, -2]),
]

cube_colors = [
    np.array([255, 0, 0]),
    np.array([0, 255, 0]),
    np.array([0, 0, 255]),
    np.array([255, 255, 0]),
]

cube_scales = [
    np.array([1, 5, 1]),
    np.array([1, 1, 1]),
    np.array([1, 1, 1]),
    np.array([5, 1, 1]),
]

cube_materials = [
    ("aluminum", "paint", "emissive"),
    ("steel", "clearcoat", "emissive"),
    ("one_way_mirror", "none", "single_sided"),
    ("concrete", "paint", "emissive"),
]

# Create a distant light to illuminate the scene and show the visual material colors
omni.kit.commands.execute(
    "CreatePrim", prim_type="DistantLight", attributes={"inputs:angle": 1.0, "inputs:intensity": 3000}
)

# Create cubes and apply materials
for i, (position, color, scale, material_tuple) in enumerate(
    zip(cube_positions, cube_colors, cube_scales, cube_materials)
):
    cube = VisualCuboid(
        prim_path=f"/World/cube_{i}",
        name=f"cube_{i}",
        position=position,
        color=color,
        scale=scale,
    )
    visual_material = OmniPBR(
        prim_path=f"/Looks/cube_{i}/material",
        name=f"cube_{i}_material",
        color=color,
    )
    apply_nonvisual_material(visual_material.prim, material_tuple[0], material_tuple[1], material_tuple[2])
    cube.apply_visual_material(visual_material)

# Manually select the non-visual material Debug View to inspect materials:
# RTX - Real-Time (in viewport) > Debug View > Non-Visual Material ID

# Run for 10 frames in test mode
i = 0
while simulation_app.is_running() and (not args.test or i < 10):
    simulation_app.update()
    i += 1

simulation_app.close()
