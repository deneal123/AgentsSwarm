#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HW2: Проведение экспериментов по методам ускорения.
"""

import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='HW2: Acceleration Experiments')
    parser.add_argument('--method', choices=['distillation', 'quantization', 'pruning', 'all'], default='all')
    parser.add_argument('--output_dir', '-o', type=str, default='results/hw2')
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--num_samples', type=int, default=500)
    parser.add_argument('--batch_size', type=int, default=16)
    args = parser.parse_args()
    
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    methods = ['distillation', 'quantization', 'pruning'] if args.method == 'all' else [args.method]
    
    for method in methods:
        print(f"\nRunning experiment: {method}...")
        cmd = [sys.executable, "src/train.py", "--epochs", str(args.epochs), "--num_samples", str(args.num_samples), "--batch_size", str(args.batch_size)]
        
        if method == 'quantization':
            cmd.append("--quantize")
        elif method == 'pruning':
            cmd.append("--prune")
        
        cmd.extend(["--output_dir", str(out_dir / method)])
        subprocess.run(cmd)
    
    print(f"\nHW2 experiments complete. Results in {out_dir}")

if __name__ == "__main__":
    main()
