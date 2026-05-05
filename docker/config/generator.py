from pathlib import Path
import re

# Isaac Sim публикует TF в /carter01/tf, но внутри frame_id = "odom", "base_link"
# (без namespace). Поэтому в nav_params НЕ заменяем frame_id.
# Заменяем ТОЛЬКО топики.
#
# Базовый nav2_params_custom.yaml должен содержать топики БЕЗ namespace:
#   scan_topic: front_2d_lidar/scan
#   topic: /front_3d_lidar/point_cloud
#   odom_topic: /chassis/odom

BASE_CONFIG = Path("./nav2_params/nav2_params_custom.yaml")

ROBOTS = {
    "carter01": {"output": Path("./nav2_params/nav2_params_carter01.yaml"), "ns": "carter01"},
    "carter02": {"output": Path("./nav2_params/nav2_params_carter02.yaml"), "ns": "carter02"},
}


def make_robot_config(base_text: str, ns: str) -> str:
    text = base_text

    # ── Odometry topic ───────────────────────────────────────────
    text = re.sub(
        r'^(\s*odom_topic:\s*).*$',
        rf'\1"/{ns}/chassis/odom"',
        text, flags=re.MULTILINE,
    )

    # ── Laser / pointcloud topics ─────────────────────────────────
    sensor_map = [
        ("/front_2d_lidar/scan",         f"/{ns}/front_2d_lidar/scan"),
        ("front_2d_lidar/scan",          f"/{ns}/front_2d_lidar/scan"),
        ("/back_2d_lidar/scan",          f"/{ns}/back_2d_lidar/scan"),
        ("back_2d_lidar/scan",           f"/{ns}/back_2d_lidar/scan"),
        ("/front_3d_lidar/point_cloud",  f"/{ns}/front_3d_lidar/point_cloud"),
        ("front_3d_lidar/point_cloud",   f"/{ns}/front_3d_lidar/point_cloud"),
        ("/front_3d_lidar/lidar_points", f"/{ns}/front_3d_lidar/lidar_points"),
        ("front_3d_lidar/lidar_points",  f"/{ns}/front_3d_lidar/lidar_points"),
    ]
    for old, new in sensor_map:
        if new not in text:
            text = text.replace(old, new)

    # ── Collision monitor cmd_vel / state topics ──────────────────
    text = re.sub(
        r'^(\s*cmd_vel_in_topic:\s*).*$',
        rf'\1"/{ns}/cmd_vel_smoothed"',
        text, flags=re.MULTILINE,
    )
    text = re.sub(
        r'^(\s*cmd_vel_out_topic:\s*).*$',
        rf'\1"/{ns}/cmd_vel"',
        text, flags=re.MULTILINE,
    )
    text = re.sub(
        r'^(\s*state_topic:\s*).*$',
        rf'\1"/{ns}/collision_monitor_state"',
        text, flags=re.MULTILINE,
    )

    # ── Footprint topics ──────────────────────────────────────────
    footprint_new = f'footprint_topic: "/{ns}/local_costmap/published_footprint"'
    for old in [
        'footprint_topic: "/local_costmap/published_footprint"',
        "footprint_topic: /local_costmap/published_footprint",
        'footprint_topic: "local_costmap/published_footprint"',
        "footprint_topic: local_costmap/published_footprint",
    ]:
        text = text.replace(old, footprint_new)

    # ── Costmap topics (behavior_server / docking_server) ─────────
    costmap_new = f'costmap_topic: "/{ns}/local_costmap/costmap_raw"'
    for old in [
        'costmap_topic: "local_costmap/costmap_raw"',
        "costmap_topic: local_costmap/costmap_raw",
    ]:
        text = text.replace(old, costmap_new)

    return text


def main() -> None:
    if not BASE_CONFIG.exists():
        print(f"ERROR: base config not found: {BASE_CONFIG}")
        return

    base_text = BASE_CONFIG.read_text(encoding="utf-8")

    for name, robot in ROBOTS.items():
        ns = robot["ns"]
        output_text = make_robot_config(base_text, ns)
        robot["output"].write_text(output_text, encoding="utf-8")
        print(f"created: {robot['output']}")

        bad = [l for l in output_text.splitlines() if "//" in l and not l.strip().startswith("#")]
        if bad:
            print(f"  WARNING: double slashes in {robot['output']}:")
            for l in bad:
                print(f"    {l.strip()}")


if __name__ == "__main__":
    main()