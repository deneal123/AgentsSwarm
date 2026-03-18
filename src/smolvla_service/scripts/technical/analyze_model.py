# -*- coding: utf-8 -*-
"""
Анализ модели SmolVLA: архитектура, параметры, FLOPs, память.
"""

import argparse
import json
import sys
import torch
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from models.teacher import RealSmolVLAModel

def main():
    parser = argparse.ArgumentParser(description='Анализ модели SmolVLA')
    parser.add_argument('--output', '-o', type=str, default='results/model_analysis.json')
    args = parser.parse_args()
    
    print("Analyzing model...")
    model = RealSmolVLAModel()
    params = model.get_num_parameters()
    
    analysis = {
        "model_name": "RealSmolVLAModel",
        "parameters": {
            "total": params,
            "total_millions": round(params / 1e6, 2),
            "size_fp32_mb": round(params * 4 / 1024 / 1024, 2)
        },
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"Model analysis saved to {output_path}")

if __name__ == "__main__":
    main()
