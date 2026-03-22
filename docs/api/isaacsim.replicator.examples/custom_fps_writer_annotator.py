# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import os

import carb.settings
import omni.kit.app
import omni.replicator.core as rep
import omni.timeline
import omni.usd

# Configuration
NUM_CAPTURES = 6
VERBOSE = True

# NOTE: To avoid FPS delta misses make sure the sensor framerate is divisible by the timeline framerate
STAGE_FPS = 100.0
SENSOR_FPS = 10.0
SENSOR_DT = 1.0 / SENSOR_FPS


def run_custom_fps_example(duration_seconds):
    # Create a new stage
    omni.usd.get_context().new_stage()

    # Set DLSS to Quality mode (2) for best SDG results , options: 0 (Performance), 1 (Balanced), 2 (Quality), 3 (Auto)
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Disable capture on play (data will only be accessed at custom times)
    carb.settings.get_settings().set("/omni/replicator/captureOnPlay", False)

    # Make sure fixed time stepping is set (the timeline will be advanced with the same delta time)
    carb.settings.get_settings().set("/app/player/useFixedTimeStepping", True)

    # Set the timeline parameters
    timeline = omni.timeline.get_timeline_interface()
    timeline.set_looping(False)
    timeline.set_current_time(0.0)
    timeline.set_end_time(10)
    timeline.set_time_codes_per_second(STAGE_FPS)
    timeline.play()
    timeline.commit()

    # Create scene with a semantically annotated cube with physics
    rep.functional.create.dome_light(intensity=250)
    cube = rep.functional.create.cube(position=(0, 0, 3), semantics={"class": "cube"})
    rep.functional.physics.apply_collider(cube)
    rep.functional.physics.apply_rigid_body(cube)

    # Create render product (disabled until data capture is needed)
    rp = rep.create.render_product("/OmniverseKit_Persp", (512, 512), name="rp")
    rp.hydra_texture.set_updates_enabled(False)

    # Create a writer and an annotator as examples of different ways of accessing data
    out_dir_rgb = os.path.join(os.getcwd(), "_out_writer_fps_rgb")
    print(f"Writer data will be written to: {out_dir_rgb}")
    writer_rgb = rep.WriterRegistry.get("BasicWriter")
    writer_rgb.initialize(output_dir=out_dir_rgb, rgb=True)
    writer_rgb.attach(rp)
    annot_depth = rep.AnnotatorRegistry.get_annotator("distance_to_camera")
    annot_depth.attach(rp)

    # Run the simulation for the given number of frames and access the data at the desired framerates
    print(
        f"Starting simulation: {duration_seconds:.2f}s duration, {SENSOR_FPS:.0f} FPS sensor, {STAGE_FPS:.0f} FPS timeline"
    )

    frame_count = 0
    previous_time = timeline.get_current_time()
    elapsed_time = 0.0
    iteration = 0

    while timeline.get_current_time() < duration_seconds:
        current_time = timeline.get_current_time()
        delta_time = current_time - previous_time
        elapsed_time += delta_time

        # Simulation progress
        if VERBOSE:
            print(f"Step {iteration}: timeline time={current_time:.3f}s, elapsed time={elapsed_time:.3f}s")

        # Trigger sensor at desired framerate (use small epsilon for floating point comparison)
        if elapsed_time >= SENSOR_DT - 1e-9:
            elapsed_time -= SENSOR_DT  # Reset with remainder to maintain accuracy

            rp.hydra_texture.set_updates_enabled(True)
            rep.orchestrator.step(delta_time=0.0, pause_timeline=False, rt_subframes=16)
            annot_data = annot_depth.get_data()

            print(f"\n  >> Capturing frame {frame_count} at time={current_time:.3f}s | shape={annot_data.shape}\n")
            frame_count += 1

            rp.hydra_texture.set_updates_enabled(False)

        previous_time = current_time
        # Advance the app (timeline) by one frame
        simulation_app.update()
        iteration += 1

    # Wait for writer to finish
    rep.orchestrator.wait_until_complete()


# Run example with duration for all captures plus a buffer of 5 frames
duration = (NUM_CAPTURES * SENSOR_DT) + (5.0 / STAGE_FPS)
run_custom_fps_example(duration_seconds=duration)

simulation_app.close()
