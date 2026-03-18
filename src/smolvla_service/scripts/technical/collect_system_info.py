# -*- coding: utf-8 -*-
"""
Сбор системной информации для всех домашних заданий.
Используется для документирования конфигурации и ограничений.

Usage:
    python src/scripts/technical/collect_system_info.py --output results/system_info.json
"""

import argparse
import json
import platform
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_gpu_info():
    if not HAS_TORCH or not torch.cuda.is_available():
        return {"available": False, "devices": []}
    
    info = {
        "available": True,
        "cuda_version": torch.version.cuda,
        "devices": []
    }
    
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        info["devices"].append({
            "id": i,
            "name": props.name,
            "total_memory_gb": round(props.total_memory / 1024**3, 2),
            "compute_capability": f"{props.major}.{props.minor}"
        })
    return info


def get_cpu_info():
    info = {"processor": platform.processor(), "machine": platform.machine()}
    if HAS_PSUTIL:
        info["cores_physical"] = psutil.cpu_count(logical=False)
        info["cores_logical"] = psutil.cpu_count(logical=True)
    return info


def get_ram_info():
    if not HAS_PSUTIL:
        return {"total_gb": None}
    mem = psutil.virtual_memory()
    return {"total_gb": round(mem.total / 1024**3, 2), "available_gb": round(mem.available / 1024**3, 2)}


def main():
    parser = argparse.ArgumentParser(description='Сбор системной информации')
    parser.add_argument('--output', '-o', type=str, default='results/system_info.json')
    args = parser.parse_args()
    
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "gpu": get_gpu_info(),
        "pytorch": torch.__version__ if HAS_TORCH else None
    }
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    print(f"System info saved to {output_path}")


if __name__ == "__main__":
    main()
