import os
from typing import Optional


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: Optional[float] = None) -> Optional[float]:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return float(val)
    except Exception:
        return default


def env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except Exception:
        return default


__all__ = ["env_bool", "env_float", "env_int"]
