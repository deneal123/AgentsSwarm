#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сбор и анализ результатов всех домашних заданий.
Генерация итоговых отчетов.

Usage:
    # Сбор результатов HW1
    python src/scripts/collect_results.py --hw 1
    
    # Сбор результатов HW2
    python src/scripts/collect_results.py --hw 2
    
    # Сбор результатов HW3
    python src/scripts/collect_results.py --hw 3
    
    # Все результаты
    python src/scripts/collect_results.py --all
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def collect_hw1_results(results_dir: Path) -> dict:
    """Сбор результатов HW1"""
    print("\n" + "="*60)
    print("HW1 RESULTS")
    print("="*60)
    
    analysis_file = results_dir / 'analysis_report.json'
    summary_file = results_dir / 'summary.json'
    
    if not analysis_file.exists():
        print("No HW1 results found")
        return {}
    
    with open(analysis_file) as f:
        data = json.load(f)
    
    # Extract key metrics
    result = {
        'model': data.get('model', {}),
        'bottlenecks': data.get('bottlenecks', {}),
    }
    
    if 'profiling' in data:
        result['profiling'] = data['profiling']
    
    # Print summary
    print(f"Model: {result['model'].get('name')}")
    print(f"Parameters: {result['model'].get('parameters'):,}")
    print(f"Size: {result['model'].get('size_fp32_mb')} MB")
    
    if 'bottlenecks' in result:
        print("\nBottlenecks:")
        for bn in result['bottlenecks'].get('breakdown', []):
            print(f"  - {bn['component']}: {bn['percentage']}%")
    
    return result


def collect_hw2_results(results_dir: Path) -> dict:
    """Сбор результатов HW2"""
    print("\n" + "="*60)
    print("HW2 RESULTS")
    print("="*60)
    
    experiments_file = results_dir / 'all_experiments.json'
    
    if not experiments_file.exists():
        print("No HW2 results found")
        return {}
    
    with open(experiments_file) as f:
        data = json.load(f)
    
    # Print summary
    print(f"Experiments run: {len(data)}")
    
    for exp in data:
        print(f"\n{exp.get('method', 'unknown')}:")
        if 'ratio' in exp:
            print(f"  Ratio: {exp['ratio']}")
        if 'compression' in exp:
            print(f"  Compression: {exp['compression']:.2f}x")
    
    return data


def collect_hw3_results(results_dir: Path) -> dict:
    """Сбор результатов HW3"""
    print("\n" + "="*60)
    print("HW3 RESULTS")
    print("="*60)
    
    constraints_file = results_dir / 'constraints_analysis.json'
    pipeline_file = results_dir / 'pipeline_results.json'
    
    results = {}
    
    if constraints_file.exists():
        with open(constraints_file) as f:
            data = json.load(f)
            results['constraints_analysis'] = data
        
        print("\nConstraints:")
        for k, v in data.get('constraints', {}).items():
            print(f"  {k}: {v}")
        
        print("\nStrategy:")
        strategy = data.get('strategy', {})
        for i, stage in enumerate(strategy.get('stages', []), 1):
            print(f"  Stage {i}: {stage['name']}")
    
    if pipeline_file.exists():
        with open(pipeline_file) as f:
            data = json.load(f)
            results['pipeline'] = data
        
        print("\nPipeline completed:")
        for stage in data.get('stages', []):
            print(f"  - {stage.get('method', 'unknown')}")
    
    if not results:
        print("No HW3 results found")
    
    return results


def generate_final_report(all_results: dict, output_dir: Path):
    """Генерация финального отчета"""
    print("\n" + "="*60)
    print("GENERATING FINAL REPORT")
    print("="*60)
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'homework_1': all_results.get('hw1', {}),
        'homework_2': all_results.get('hw2', {}),
        'homework_3': all_results.get('hw3', {}),
    }
    
    with open(output_dir / 'final_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Generate markdown report
    md_path = output_dir / 'final_report.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Final Report: SmolVLA Optimization\n\n")
        f.write(f"Generated: {report['generated_at']}\n\n")
        
        # HW1 Summary
        if 'hw1' in report and report['hw1']:
            f.write("## Homework 1: Model Analysis\n\n")
            model = report['hw1'].get('model', {})
            f.write(f"- Model: {model.get('name')}\n")
            f.write(f"- Parameters: {model.get('parameters'):,}\n")
            f.write(f"- Size: {model.get('size_fp32_mb')} MB\n\n")
        
        # HW2 Summary
        if 'hw2' in report and report['hw2']:
            f.write("## Homework 2: Optimization Experiments\n\n")
            f.write(f"Experiments: {len(report['hw2'])}\n\n")
        
        # HW3 Summary
        if 'hw3' in report and report['hw3']:
            f.write("## Homework 3: System Design\n\n")
            constraints = report['hw3'].get('constraints_analysis', {}).get('constraints', {})
            if constraints:
                f.write("### Constraints\n\n")
                for k, v in constraints.items():
                    f.write(f"- **{k}**: {v}\n")
    
    print(f"Report saved to: {output_dir / 'final_report.json'}")
    print(f"Markdown saved to: {md_path}")


def main():
    parser = argparse.ArgumentParser(description='Collect results from all homeworks')
    parser.add_argument('--hw', type=int, choices=[1, 2, 3],
                        help='Specific homework to collect')
    parser.add_argument('--all', action='store_true',
                        help='Collect all results')
    parser.add_argument('--output', '-o', type=str, default='results',
                        help='Output directory')
    args = parser.parse_args()
    
    results_dir = Path(args.output)
    all_results = {}
    
    if args.all or args.hw == 1:
        hw1_dir = results_dir / 'hw1'
        if hw1_dir.exists():
            all_results['hw1'] = collect_hw1_results(hw1_dir)
    
    if args.all or args.hw == 2:
        hw2_dir = results_dir / 'hw2'
        if hw2_dir.exists():
            all_results['hw2'] = collect_hw2_results(hw2_dir)
    
    if args.all or args.hw == 3:
        hw3_dir = results_dir / 'hw3'
        if hw3_dir.exists():
            all_results['hw3'] = collect_hw3_results(hw3_dir)
    
    if args.all:
        generate_final_report(all_results, results_dir)
    
    print("\n" + "="*60)
    print("DONE")
    print("="*60)


if __name__ == "__main__":
    main()
