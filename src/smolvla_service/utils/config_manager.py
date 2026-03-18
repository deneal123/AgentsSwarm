"""
Configuration Management System for Model Optimization Experiments
Provides centralized configuration handling and experiment tracking
"""

import json
import yaml
import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QuantizationConfig:
    """Configuration for quantization experiments"""
    method: str = "dynamic"  # dynamic, static, manual
    dtype: str = "int8"      # int8, int4, fp16
    calibration_batches: int = 10
    modules_to_quantize: List[str] = None
    
    def __post_init__(self):
        if self.modules_to_quantize is None:
            self.modules_to_quantize = ["nn.Linear"]

@dataclass  
class DistillationConfig:
    """Configuration for knowledge distillation experiments"""
    student_reduction_factor: float = 0.5
    temperature: float = 3.0
    alpha: float = 0.7  # weight balance between distill and task loss
    num_epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 1e-4

@dataclass
class PruningConfig:
    """Configuration for pruning experiments"""
    attention_head_pruning_ratio: float = 0.3
    ffn_width_pruning_ratio: float = 0.3
    structured_pruning: bool = True
    magnitude_based: bool = True

@dataclass
class MixedPrecisionConfig:
    """Configuration for mixed precision training"""
    precision: str = "fp16"  # fp16, bf16, fp32
    amp_enabled: bool = True
    gradient_scaling: bool = True
    loss_scale: float = 128.0

@dataclass
class ExperimentConfig:
    """Main experiment configuration"""
    experiment_name: str
    model_name: str = "smolvla"
    quantization: QuantizationConfig = None
    distillation: DistillationConfig = None
    pruning: PruningConfig = None
    mixed_precision: MixedPrecisionConfig = None
    output_dir: str = "experiments"
    seed: int = 42
    device: str = "cuda" if "cuda" in str(__import__('torch').cuda.is_available()) else "cpu"
    
    def __post_init__(self):
        if self.quantization is None:
            self.quantization = QuantizationConfig()
        if self.distillation is None:
            self.distillation = DistillationConfig()
        if self.pruning is None:
            self.pruning = PruningConfig()
        if self.mixed_precision is None:
            self.mixed_precision = MixedPrecisionConfig()

class ConfigManager:
    """Manages experiment configurations and tracking"""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = config_dir
        self.experiments_dir = "experiments"
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(self.experiments_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def create_default_configs(self) -> Dict[str, ExperimentConfig]:
        """Create default experiment configurations"""
        configs = {}
        
        # Basic quantization experiment
        configs["quantization_basic"] = ExperimentConfig(
            experiment_name="quantization_basic",
            quantization=QuantizationConfig(
                method="dynamic",
                dtype="int8",
                calibration_batches=5
            )
        )
        
        # Comprehensive optimization experiment
        configs["comprehensive_optimization"] = ExperimentConfig(
            experiment_name="comprehensive_optimization",
            quantization=QuantizationConfig(
                method="dynamic",
                dtype="fp16"
            ),
            distillation=DistillationConfig(
                student_reduction_factor=0.3,
                num_epochs=5
            ),
            pruning=PruningConfig(
                attention_head_pruning_ratio=0.2,
                ffn_width_pruning_ratio=0.3
            ),
            mixed_precision=MixedPrecisionConfig(
                precision="fp16",
                amp_enabled=True
            )
        )
        
        # Ablation study configurations
        configs["ablation_distillation_only"] = ExperimentConfig(
            experiment_name="ablation_distillation_only",
            distillation=DistillationConfig(
                student_reduction_factor=0.5,
                num_epochs=8
            )
        )
        
        configs["ablation_pruning_only"] = ExperimentConfig(
            experiment_name="ablation_pruning_only",
            pruning=PruningConfig(
                attention_head_pruning_ratio=0.4,
                ffn_width_pruning_ratio=0.5
            )
        )
        
        return configs
    
    def save_config(self, config: ExperimentConfig, filename: Optional[str] = None) -> str:
        """Save configuration to file"""
        if filename is None:
            filename = f"{config.experiment_name}.json"
        
        filepath = os.path.join(self.config_dir, filename)
        
        try:
            # Convert dataclass to dictionary
            config_dict = asdict(config)
            
            # Save as JSON
            with open(filepath, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            self.logger.info(f"Configuration saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def load_config(self, filepath: str) -> ExperimentConfig:
        """Load configuration from file"""
        try:
            with open(filepath, 'r') as f:
                config_dict = json.load(f)
            
            # Handle nested configurations
            if 'quantization' in config_dict and config_dict['quantization']:
                config_dict['quantization'] = QuantizationConfig(**config_dict['quantization'])
            if 'distillation' in config_dict and config_dict['distillation']:
                config_dict['distillation'] = DistillationConfig(**config_dict['distillation'])
            if 'pruning' in config_dict and config_dict['pruning']:
                config_dict['pruning'] = PruningConfig(**config_dict['pruning'])
            if 'mixed_precision' in config_dict and config_dict['mixed_precision']:
                config_dict['mixed_precision'] = MixedPrecisionConfig(**config_dict['mixed_precision'])
            
            config = ExperimentConfig(**config_dict)
            self.logger.info(f"Configuration loaded from: {filepath}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def create_experiment_directory(self, config: ExperimentConfig) -> str:
        """Create directory structure for experiment"""
        experiment_dir = os.path.join(self.experiments_dir, config.experiment_name)
        os.makedirs(experiment_dir, exist_ok=True)
        
        # Create subdirectories
        subdirs = ["checkpoints", "logs", "results", "configs"]
        for subdir in subdirs:
            subdir_path = os.path.join(experiment_dir, subdir)
            os.makedirs(subdir_path, exist_ok=True)
        
        # Save configuration in experiment directory
        config_path = os.path.join(experiment_dir, "configs", "experiment_config.json")
        # Ensure the configs directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        self.save_config(config, config_path)
        
        self.logger.info(f"Experiment directory created: {experiment_dir}")
        return experiment_dir
    
    def log_experiment_start(self, config: ExperimentConfig, experiment_dir: str):
        """Log experiment start information"""
        log_file = os.path.join(experiment_dir, "logs", "experiment.log")
        
        # Create experiment metadata
        metadata = {
            "experiment_name": config.experiment_name,
            "start_time": datetime.now().isoformat(),
            "config": asdict(config),
            "system_info": self._get_system_info()
        }
        
        # Save metadata
        metadata_path = os.path.join(experiment_dir, "configs", "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        self.logger.info(f"Experiment '{config.experiment_name}' started")
        self.logger.info(f"Configuration saved to: {metadata_path}")
        return metadata_path
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for experiment logging"""
        import torch
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "cpu_count": psutil.cpu_count(),
            "total_memory_gb": psutil.virtual_memory().total / (1024**3)
        }
    
    def generate_config_summary(self, config: ExperimentConfig) -> str:
        """Generate human-readable summary of configuration"""
        summary = []
        summary.append(f"Experiment: {config.experiment_name}")
        summary.append(f"Model: {config.model_name}")
        summary.append(f"Device: {config.device}")
        summary.append("")
        
        if config.quantization:
            summary.append("Quantization:")
            summary.append(f"  Method: {config.quantization.method}")
            summary.append(f"  Dtype: {config.quantization.dtype}")
            summary.append("")
        
        if config.distillation:
            summary.append("Distillation:")
            summary.append(f"  Student size: {config.distillation.student_reduction_factor*100:.0f}%")
            summary.append(f"  Epochs: {config.distillation.num_epochs}")
            summary.append("")
        
        if config.pruning:
            summary.append("Pruning:")
            summary.append(f"  Attention pruning: {config.pruning.attention_head_pruning_ratio*100:.0f}%")
            summary.append(f"  FFN pruning: {config.pruning.ffn_width_pruning_ratio*100:.0f}%")
            summary.append("")
        
        if config.mixed_precision:
            summary.append("Mixed Precision:")
            summary.append(f"  Precision: {config.mixed_precision.precision}")
            summary.append(f"  AMP: {config.mixed_precision.amp_enabled}")
        
        return "\n".join(summary)

# Example usage and demonstration
if __name__ == "__main__":
    # Initialize config manager
    config_manager = ConfigManager()
    
    # Create default configurations
    default_configs = config_manager.create_default_configs()
    
    logger.info("Available default configurations:")
    for name, config in default_configs.items():
        logger.info(f"\n{name}:")
        logger.info(config_manager.generate_config_summary(config))
        logger.info("-" * 50)
    
    # Save all default configurations
    for name, config in default_configs.items():
        config_manager.save_config(config)
    
    # Demonstrate experiment directory creation
    test_config = default_configs["comprehensive_optimization"]
    experiment_dir = config_manager.create_experiment_directory(test_config)
    config_manager.log_experiment_start(test_config, experiment_dir)
    
    logger.info(f"\nCreated experiment directory: {experiment_dir}")
