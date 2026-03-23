from __future__ import annotations

import pytest

from nvidia_isaac_simulation.robots.wheeled import WheeledRobotSpawner


def test_validate_robot_names_count_uses_fallback_names_when_not_provided():
    names = WheeledRobotSpawner.validate_robot_names_count(2, None)

    assert names == ["robot_0", "robot_1"]


def test_validate_robot_names_count_returns_explicit_names_when_lengths_match():
    names = WheeledRobotSpawner.validate_robot_names_count(2, ["carter1", "carter2"])

    assert names == ["carter1", "carter2"]


def test_validate_robot_names_count_raises_when_lengths_do_not_match():
    with pytest.raises(ValueError, match="Length of robot_names must match count"):
        WheeledRobotSpawner.validate_robot_names_count(2, ["carter1"])