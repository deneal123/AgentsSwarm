# SmolVLA Model Optimization Framework

A comprehensive framework for optimizing SmolVLA (Vision-Language-Action) models for robotics applications using knowledge distillation, quantization, and other optimization techniques.

## Reports

- [ReportHW1](https://github.com/deneal123/destil/blob/dev/docs/hw1_report.md)
- [ReportHW2](https://github.com/deneal123/destil/blob/dev/docs/hw2_report.md)
- [ReportHW3](https://github.com/deneal123/destil/blob/dev/docs/hw3_report.md)


## Features

- **Knowledge Distillation**: Teacher-student architecture with advanced loss functions
- **Model Compression**: Up to 85% size reduction (6.8x compression)
- **Speed Optimization**: 20-25x inference speedup
- **Mixed Precision Training**: FP16 support for faster training
- **ONNX Export**: Ready for production deployment
- **Enhanced Architecture**: CNN encoder + Transformer with positional encoding
- **Advanced Distillation**: Multi-component loss with attention transfer
- **Real Dataset Support**: LeRobot integration with fallback to simulated data
- **Comprehensive Monitoring**: Detailed training metrics and early stopping

## Installation

```bash
# Install dependencies using uv
uv sync

# Or install with pip
pip install -e .
```

## Quick Start

### Basic Training

```bash
# Real SmolVLA training with HuggingFace integration
python scripts/train.py --epochs 10 --dataset lerobot/pusht

# Quick test with small dataset
python scripts/train.py --epochs 5 --num_samples 500 --batch_size 16

# Full optimization pipeline
python scripts/train.py --epochs 20 --profile --quantize --prune --mixed_precision
```

### Advanced Training Options

```bash
# Enable profiling and optimization analysis
python scripts/train.py --epochs 10 --profile --quantize --prune

# Mixed precision with real profiling
python scripts/train.py --epochs 15 --mixed_precision --profile

# Custom dataset and model
python scripts/train.py --dataset lerobot/aloha_static_coffee --model_id lerobot/smolvla_base

# Full optimization pipeline with custom dataset settings
python scripts/train.py --epochs 20 --profile --quantize --prune --mixed_precision \
  --dataset_cache_dir ./my_datasets --dataset_percentage 0.1

# Using environment variables
export HF_DATASETS_CACHE="./datasets_cache"
export DATASET_DOWNLOAD_PERCENTAGE="0.5"
python scripts/train.py --epochs 10
```

### Export and Deployment

```bash
# Export trained model to ONNX
python scripts/export_onnx.py --model_path results/best_model.pth
```

### Arguments

| Argument | Description | Default |
|----------|-------------|----------|
| `--model_id` | HuggingFace model ID | lerobot/smolvla_base |
| `--dataset` | Dataset name | lerobot/pusht |
| `--epochs` | Number of training epochs | 10 |
| `--batch_size` | Training batch size | 32 |
| `--num_samples` | Number of training samples | 2000 |
| `--lr` | Learning rate | 1e-4 |
| `--student_ratio` | Student model size ratio (0.1-0.9) | 0.5 |
| `--temperature` | Distillation temperature | 3.0 |
| `--alpha` | Distillation loss weight | 0.7 |
| `--mixed_precision` | Enable mixed precision training | False |
| `--profile` | Enable performance profiling | False |
| `--quantize` | Analyze quantization potential | False |
| `--prune` | Analyze pruning potential | False |
| `--dataset_cache_dir` | Custom dataset cache directory | None |
| `--dataset_percentage` | Dataset percentage (0.0-1.0) | None |
| `--output_dir` | Output directory | results/real_optimization |

## Project Structure

```
smolvla-optimization/
├── src/
│   ├── models/           # Model architectures and optimization techniques
│   │   ├── __init__.py
│   │   ├── teacher.py    # RealSmolVLAModel (teacher model)
│   │   ├── student.py    # Student model implementation
│   │   ├── distillation.py # Knowledge distillation framework
│   │   ├── quantization.py # Quantization utilities
│   │   └── smolvla_analysis.py # Model analysis tools
│   ├── datasets/         # Dataset classes and management
│   │   ├── __init__.py
│   │   ├── dataset_manager.py
│   │   └── real_dataset.py # RealLeRobotDataset
│   ├── training/         # Training utilities and optimizers
│   │   ├── __init__.py
│   │   ├── trainer.py    # Distillation trainer
│   │   └── optimizers.py # Optimization algorithms
│   └── utils/            # Utility functions
│       ├── __init__.py
│       ├── config_manager.py # Configuration management
│       ├── logger.py     # Logging utilities
│       ├── profiler.py   # Performance profiling
│       └── quality_assessment.py # Quality assessment tools
├── scripts/              # Entry point scripts
│   ├── train.py          # Main training script
│   └── export_onnx.py    # Model export utility
├── configs/              # Configuration files
│   └── config.json       # Default configuration
├── docs/                 # Documentation
├── results/              # Output results
│   └── real_optimization/ # Default results directory
├── tests/                # Unit and integration tests
│   ├── unit/
│   └── integration/
├── .env                  # Environment variables
├── .env.example          # Example environment variables
├── pyproject.toml        # Project dependencies and metadata
└── README.md             # This file
```

## Configuration

### Environment Variables

Create a `.env` file from `.env.example` to configure the project:

```bash
# Copy example configuration
cp .env.example .env

# Edit .env file with your settings
```

Key environment variables:
- `HF_DATASETS_CACHE` - Dataset cache directory
- `DATASET_DOWNLOAD_PERCENTAGE` - Fraction of dataset to use (0.01-1.0)
- `SMOLVLA_MODEL_ID` - Default SmolVLA model ID
- `DEFAULT_EPOCHS` - Default number of training epochs
- `DEFAULT_BATCH_SIZE` - Default batch size
- `DEFAULT_LEARNING_RATE` - Default learning rate
- `ENABLE_MIXED_PRECISION` - Enable FP16 training
- `ENABLE_PROFILING` - Enable performance profiling
- `OUTPUT_DIR` - Default output directory

## License

MIT License
