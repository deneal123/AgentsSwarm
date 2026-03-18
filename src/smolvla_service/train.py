import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
import argparse
import logging
import time
import numpy as np
import random
from torch.utils.data import DataLoader

from src.models.teacher import RealSmolVLAModel
from src.models.student import StudentModel
from src.models.distillation import DistillationLoss
from src.datasets.real_dataset import RealLeRobotDataset, collate_fn
from src.training.trainer import DistillationTrainer
from src.training.optimizers import OptimizationManager
from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def set_seed(seed: int = 42):
    """Set random seed for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    logger.info(f"Random seed set to {seed}")


def parse_args():
    parser = argparse.ArgumentParser(description="SmolVLA Knowledge Distillation Training")
    parser.add_argument('--model_id', type=str, default='lerobot/smolvla_base')
    parser.add_argument('--dataset', type=str, default='lerobot/libero')
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--num_samples', type=int, default=1000)
    parser.add_argument('--lr', type=float, default=5e-5)
    parser.add_argument('--student_ratio', type=float, default=0.5)
    parser.add_argument('--temperature', type=float, default=1.0)
    parser.add_argument('--alpha', type=float, default=0.5)
    parser.add_argument('--mixed_precision', action='store_true')
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--quantize', action='store_true')
    parser.add_argument('--prune', action='store_true')
    parser.add_argument('--dataset_cache_dir', type=str, default=None)
    parser.add_argument('--dataset_percentage', type=float, default=None)
    parser.add_argument('--output_dir', type=str, default='results/real_optimization')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    return parser.parse_args()


def setup_device():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    return device
    

def create_dataloaders(args, device):
    train_dataset = RealLeRobotDataset(
        dataset_name=args.dataset,
        split='train',
        num_samples=args.num_samples,
        cache_dir=args.dataset_cache_dir,
        percentage=args.dataset_percentage
    )
    val_dataset = RealLeRobotDataset(
        dataset_name=args.dataset,
        split='val',
        num_samples=args.num_samples,
        cache_dir=args.dataset_cache_dir,
        percentage=args.dataset_percentage
    )
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=args.batch_size, 
        shuffle=True,
        num_workers=2,
        pin_memory=True,
        collate_fn=collate_fn
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=True,
        collate_fn=collate_fn
    )
    
    logger.info(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    return train_loader, val_loader, train_dataset


def get_action_dim(dataset):
    if hasattr(dataset, 'action_dim'):
        return dataset.action_dim
    if len(dataset) > 0:
        sample = dataset[0]
        if isinstance(sample, dict):
            action = sample.get('action')
        else:
            _, _, action = sample
        return action.shape[-1] if action.dim() > 0 else action.shape[0]
    return 7


def create_models(args, device, action_dim):
    logger.info(f"Creating teacher model (SmolVLA)...")
    # Pass device to teacher so it uses correct device
    teacher = RealSmolVLAModel(model_id=args.model_id, action_dim=action_dim, device=device)
    teacher_params = teacher.get_num_parameters()
    logger.info(f"Teacher parameters: {teacher_params:,}")
    
    # Get action dim from teacher (should be 6 for SmolVLA)
    teacher_action_dim = teacher.get_action_dim()
    logger.info(f"Teacher action dim: {teacher_action_dim}")
    
    logger.info(f"Creating student model (ratio={args.student_ratio})...")
    # Student should match teacher output dimension for proper distillation
    student = StudentModel(ratio=args.student_ratio, action_dim=teacher_action_dim, state_dim=6)
    student.to(device)
    student_params = student.get_num_parameters()
    logger.info(f"Student parameters: {student_params:,}")
    logger.info(f"Compression ratio: {teacher_params/student_params:.2f}x")
    
    return teacher, student


def train(args):
    set_seed(args.seed)
    device = setup_device()
    os.makedirs(args.output_dir, exist_ok=True)
    
    train_loader, val_loader, train_dataset = create_dataloaders(args, device)
    action_dim = get_action_dim(train_dataset)
    logger.info(f"Action dimension: {action_dim}")
    
    teacher, student = create_models(args, device, action_dim)
    
    criterion = DistillationLoss(
        temperature=args.temperature,
        alpha=args.alpha
    )
    
    optimizer = torch.optim.AdamW(
        student.parameters(),
        lr=args.lr,
        weight_decay=0.01
    )
    
    scaler = torch.cuda.amp.GradScaler() if args.mixed_precision else None
    
    trainer = DistillationTrainer(
        teacher=teacher,
        student=student,
        criterion=criterion,
        optimizer=optimizer,
        device=device,
        scaler=scaler,
        output_dir=args.output_dir,
        use_profiling=args.profile
    )
    
    student = trainer.train(train_loader, val_loader, args.epochs)
    
    if args.quantize or args.prune:
        opt_manager = OptimizationManager()
        analysis = opt_manager.analyze_model(student)
        logger.info(f"Model analysis: {analysis}")
    
    if args.profile:
        from src.utils.profiler import Profiler
        logger.info("Profiling models...")
        
        # Teacher profiling
        teacher_profiler = Profiler(teacher, device)
        # Assuming input shape for teacher is (batch, 6, 256, 256) and (batch, 8)
        # But Profiler.measure_latency expects single input_shape
        # We need a more compatible profiling approach or adjust Profiler
        logger.info("Profiling teacher (skipped due to complex input)...")
        
    compression_ratio = teacher.get_num_parameters() / student.get_num_parameters()

    logger.info(f"\nFinal Results:")
    logger.info(f"  Compression: {compression_ratio:.2f}x")
    logger.info(f"  Student params: {student.get_num_parameters():,}")
    logger.info(f"  Best Val Loss: {trainer.best_loss:.4f}")
    
    return student


def main():
    args = parse_args()
    logger.info("Starting SmolVLA optimization training")
    logger.info(f"Dataset: {args.dataset}, Epochs: {args.epochs}, Batch size: {args.batch_size}")
    
    train(args)
    
    logger.info("Training completed")


if __name__ == '__main__':
    main()