#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HW3: Системное проектирование и запуск полного пайплайна.
"""

import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='HW3: Full Optimization Pipeline')
    parser.add_argument('--output_dir', '-o', type=str, default='results/hw3')
    args = parser.parse_args()
    
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nRunning full optimization pipeline (Distillation + Pruning + Quantization)...")
    cmd = [
        sys.executable, "src/train.py",
        "--epochs", "10",
        "--quantize",
        "--prune",
        "--mixed_precision",
        "--profile",
        "--output_dir", str(out_dir / "full_pipeline")
    ]
    subprocess.run(cmd)
    
    # Export to ONNX as final step
    print("\nExporting optimized model to ONNX...")
    # Assume best model is in the output dir
    model_path = out_dir / "full_pipeline" / "best_model.pth"
    if model_path.exists():
        subprocess.run([
            sys.executable, "src/export_onnx.py",
            "--model_path", str(model_path),
            "--output_dir", str(out_dir / "onnx")
        ])
    
    print(f"\nHW3 pipeline complete. Results in {out_dir}")

if __name__ == "__main__":
    main()
