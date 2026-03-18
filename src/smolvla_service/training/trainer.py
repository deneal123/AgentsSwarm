import torch
import torch.nn as nn
import torch.nn.functional as F
import time
import logging
import os
from typing import Dict, Any, Optional
from torch.cuda.amp import autocast, GradScaler

logger = logging.getLogger(__name__)


class DistillationTrainer:
    
    def __init__(self, teacher: nn.Module, student: nn.Module, criterion: nn.Module,
                 optimizer: torch.optim.Optimizer, device: torch.device,
                 scaler: Optional[GradScaler] = None, output_dir: str = 'results',
                 use_profiling: bool = False):
        self.teacher = teacher
        self.student = student
        self.criterion = criterion
        self.optimizer = optimizer
        self.device = device
        self.scaler = scaler
        self.output_dir = output_dir
        self.use_profiling = use_profiling
        
        # Freeze teacher completely - no gradients should flow through it
        self.teacher.eval()
        for param in self.teacher.parameters():
            param.requires_grad = False
        
        self.best_loss = float('inf')
        
        os.makedirs(output_dir, exist_ok=True)
    
        logger.info(f"Teacher model frozen - {sum(1 for p in teacher.parameters() if not p.requires_grad)} parameters locked")
    
    def train_epoch(self, train_loader, epoch: int) -> Dict[str, float]:
        self.student.train()
        
        total_loss = 0
        total_task = 0
        total_distill = 0
        num_batches = 0
        
        for batch_idx, batch in enumerate(train_loader):
            # Handle both dict and tuple formats
            if isinstance(batch, dict):
                images = batch.get('images', batch.get('image'))
                states = batch.get('state')
                actions = batch.get('action')
                task = batch.get('task')
                task_index = batch.get('task_index')
            else:
                images, states, actions = batch
                task = None
                task_index = None
            
            images = images.to(self.device)
            states = states.to(self.device)
            actions = actions.to(self.device)
            
            # Align state dimensions: teacher expects 6, LIBERO has 8
            if states.shape[-1] > 6:
                states = states[..., :6]
            
            # Teacher is frozen and in eval mode - no gradients
            with torch.no_grad():
                teacher_actions = self.teacher(images, states, task=task, task_index=task_index)
            
            # Student is trainable
            student_actions = self.student(images, states)
            
            # Align output dimensions: teacher may output fewer actions than student expects
            if student_actions.shape[-1] > teacher_actions.shape[-1]:
                student_actions = student_actions[..., :teacher_actions.shape[-1]]
                actions = actions[..., :teacher_actions.shape[-1]]
            
            if self.scaler is not None:
                with autocast():
                    loss, task_loss, distill_loss = self.criterion.get_components(
                        student_actions, teacher_actions, actions
                    )
                
                self.scaler.scale(loss).backward()
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                loss, task_loss, distill_loss = self.criterion.get_components(
                    student_actions, teacher_actions, actions
                )
                
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
            
            total_loss += loss.item()
            total_task += task_loss.item()
            total_distill += distill_loss.item()
            num_batches += 1
        
        return {
            'loss': total_loss / num_batches,
            'task_loss': total_task / num_batches,
            'distill_loss': total_distill / num_batches
        }
    
    @torch.no_grad()
    def compute_metrics(self, predictions: torch.Tensor, targets: torch.Tensor) -> Dict[str, float]:
        """Compute detailed regression metrics."""
        # MSE
        mse = F.mse_loss(predictions, targets).item()
        
        # MAE
        mae = F.l1_loss(predictions, targets).item()
        
        # RMSE
        rmse = torch.sqrt(F.mse_loss(predictions, targets)).item()
        
        # R² Score
        ss_res = torch.sum((targets - predictions) ** 2).item()
        ss_tot = torch.sum((targets - targets.mean()) ** 2).item()
        r2 = 1 - (ss_res / (ss_tot + 1e-8))
        
        # Per-action metrics
        action_mae = F.l1_loss(predictions, targets, reduction='none').mean(dim=0)
        per_action_mae = action_mae.cpu().tolist()
        
        return {
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'per_action_mae': per_action_mae
        }
    
    @torch.no_grad()
    def validate(self, val_loader) -> Dict[str, float]:
        self.student.eval()
        self.teacher.eval()
        
        student_metrics = {
            'mse': 0,
            'mae': 0,
            'rmse': 0,
            'r2': 0,
            'per_action_mae': [0.0] * 7
        }
        teacher_metrics = {
            'mse': 0,
            'mae': 0,
            'rmse': 0,
            'r2': 0,
            'per_action_mae': [0.0] * 7
        }
        num_batches = 0
        
        for batch in val_loader:
            # Handle both dict and tuple formats
            if isinstance(batch, dict):
                images = batch.get('images', batch.get('image'))
                states = batch.get('state')
                actions = batch.get('action')
                task = batch.get('task')
                task_index = batch.get('task_index')
            else:
                images, states, actions = batch
                task = None
                task_index = None
            
            images = images.to(self.device)
            states = states.to(self.device)
            actions = actions.to(self.device)
            
            # Align state dimensions
            if states.shape[-1] > 6:
                states = states[..., :6]
            
            # Student predictions
            student_actions = self.student(images, states)
            
            # Teacher predictions (needed before aligning actions)
            teacher_actions = self.teacher(images, states, task=task, task_index=task_index)
            
            # Align output dimensions
            if student_actions.shape[-1] > teacher_actions.shape[-1]:
                student_actions = student_actions[..., :teacher_actions.shape[-1]]
                actions = actions[..., :teacher_actions.shape[-1]]
            
            student_batch = self.compute_metrics(student_actions, actions)
            teacher_batch = self.compute_metrics(teacher_actions, actions)
            
            # Accumulate metrics
            for key in ['mse', 'mae', 'rmse', 'r2']:
                student_metrics[key] += student_batch[key]
                teacher_metrics[key] += teacher_batch[key]
            
            # Per-action MAE - use actual action dimension
            action_dim = min(len(student_batch['per_action_mae']), len(teacher_batch['per_action_mae']))
            for i in range(action_dim):
                student_metrics['per_action_mae'][i] += student_batch['per_action_mae'][i]
                teacher_metrics['per_action_mae'][i] += teacher_batch['per_action_mae'][i]
            
            num_batches += 1
        
        # Average metrics
        for key in ['mse', 'mae', 'rmse', 'r2']:
            student_metrics[key] /= num_batches
            teacher_metrics[key] /= num_batches
        
        # Per-action MAE - use actual size
        action_dim = len(student_metrics['per_action_mae'])
        for i in range(action_dim):
            student_metrics['per_action_mae'][i] /= num_batches
            teacher_metrics['per_action_mae'][i] /= num_batches
        
        # Combine results
        return {
            'val_loss': student_metrics['mse'],
            'teacher_val_loss': teacher_metrics['mse'],
            'student_mae': student_metrics['mae'],
            'teacher_mae': teacher_metrics['mae'],
            'student_rmse': student_metrics['rmse'],
            'teacher_rmse': teacher_metrics['rmse'],
            'student_r2': student_metrics['r2'],
            'teacher_r2': teacher_metrics['r2'],
            'student_per_action_mae': student_metrics['per_action_mae'],
            'teacher_per_action_mae': teacher_metrics['per_action_mae']
        }
    
    def train(self, train_loader, val_loader, num_epochs: int):
        logger.info(f"Starting training for {num_epochs} epochs")
        
        val_metrics = {}
        for epoch in range(num_epochs):
            start_time = time.time()
            
            train_metrics = self.train_epoch(train_loader, epoch)
            val_metrics = self.validate(val_loader)
            
            epoch_time = time.time() - start_time
            
            # Calculate gaps
            mse_gap = val_metrics['val_loss'] - val_metrics['teacher_val_loss']
            mae_gap = val_metrics['student_mae'] - val_metrics['teacher_mae']
            r2_gap = val_metrics['student_r2'] - val_metrics['teacher_r2']
            
            # Log main metrics
            logger.info(f"Epoch {epoch+1}/{num_epochs} | "
                       f"Train Loss: {train_metrics['loss']:.4f} | "
                       f"Task Loss: {train_metrics['task_loss']:.4f} | "
                       f"Distill Loss: {train_metrics['distill_loss']:.4f} | "
                       f"Time: {epoch_time:.2f}s")
            
            # Log validation metrics
            logger.info(f"  Val MSE | Student: {val_metrics['val_loss']:.4f} | Teacher: {val_metrics['teacher_val_loss']:.4f} | Gap: {mse_gap:+.4f}")
            logger.info(f"  Val MAE | Student: {val_metrics['student_mae']:.4f} | Teacher: {val_metrics['teacher_mae']:.4f} | Gap: {mae_gap:+.4f}")
            logger.info(f"  Val R²  | Student: {val_metrics['student_r2']:.4f} | Teacher: {val_metrics['teacher_r2']:.4f} | Gap: {r2_gap:+.4f}")
            
            # Log per-action MAE for first epoch and last epoch
            if epoch == 0 or epoch == num_epochs - 1:
                logger.info(f"  Per-Action MAE (Student): {[f'{x:.4f}' for x in val_metrics['student_per_action_mae']]}")
                logger.info(f"  Per-Action MAE (Teacher): {[f'{x:.4f}' for x in val_metrics['teacher_per_action_mae']]}")
            
            if val_metrics['val_loss'] < self.best_loss:
                self.best_loss = val_metrics['val_loss']
                self._save_checkpoint('best_model.pth', epoch, val_metrics)
        
        self._save_checkpoint('final_model.pth', num_epochs - 1, val_metrics)
        
        return self.student
    
    def _save_checkpoint(self, filename: str, epoch: int, metrics: Dict[str, Any]):
        path = os.path.join(self.output_dir, filename)
        
        torch.save({
            'epoch': epoch,
            'student_state_dict': self.student.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'metrics': metrics,
            'best_loss': self.best_loss
        }, path)
        
        logger.info(f"Checkpoint saved: {path}")


def apply_structured_pruning(model: nn.Module, sparsity: float = 0.3):
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            mask = torch.rand(module.weight.shape) > sparsity
            module.weight.data *= mask.float().to(module.weight.device)
    
    return model


def apply_attention_head_pruning(model: nn.Module, sparsity: float = 0.3):
    return model
