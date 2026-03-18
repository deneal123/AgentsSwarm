#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HW1: Сбор данных для отчета по анализу модели и bottlenecks.
"""

import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='HW1: Model Analysis and Bottlenecks')
    parser.add_argument('--output_dir', '-o', type=str, default='results/hw1')
    args = parser.parse_args()
    
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Collect system info
    print("Step 1: Collecting system info...")
    subprocess.run([sys.executable, "src/scripts/technical/collect_system_info.py", "--output", str(out_dir / "system_info.json")])
    
    # 2. Analyze model
    print("Step 2: Analyzing model architecture...")
    subprocess.run([sys.executable, "src/scripts/technical/analyze_model.py", "--output", str(out_dir / "model_analysis.json")])
    
    # 3. Run profiling using main training script with profile flag
    print("Step 3: Profiling model (inference latency/throughput)...")
    subprocess.run([
        sys.executable, "src/train.py", 
        "--epochs", "0", 
        "--profile", 
        "--output_dir", str(out_dir / "profile")
    ])
    
    print(f"\nHW1 data collection complete. Results in {out_dir}")

if __name__ == "__main__":
    main()
