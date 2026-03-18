import torch
import torch.nn as nn
import torch.nn.functional as F


class DistillationLoss(nn.Module):
    """
    Simplified distillation loss for regression tasks.
    
    For action prediction (regression), we use MSE between student and teacher outputs
    instead of KL divergence which is designed for classification.
    """
    
    def __init__(self, temperature: float = 1.0, alpha: float = 0.5):
        """
        Args:
            temperature: Not used for regression, kept for API compatibility
            alpha: Weight for distillation loss (0.5 = equal balance)
        """
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha
    
    def forward(self, student_logits: torch.Tensor, 
                teacher_logits: torch.Tensor,
                true_actions: torch.Tensor):
        """
        Compute combined loss: alpha * distillation_loss + (1 - alpha) * task_loss
        
        For regression:
        - distillation_loss: MSE between student and teacher outputs
        - task_loss: MSE between student and true actions
        """
        # Align dimensions: use minimum size
        min_dim = min(student_logits.shape[-1], teacher_logits.shape[-1], true_actions.shape[-1])
        student_logits = student_logits[..., :min_dim]
        teacher_logits = teacher_logits[..., :min_dim]
        true_actions = true_actions[..., :min_dim]
        
        # Task loss: MSE between student predictions and ground truth
        task_loss = F.mse_loss(student_logits, true_actions)
        
        # Distillation loss: MSE between student and teacher predictions
        # This teaches student to mimic teacher's behavior
        distill_loss = F.mse_loss(student_logits, teacher_logits)
        
        # Combined loss
        total_loss = self.alpha * distill_loss + (1 - self.alpha) * task_loss
        
        return total_loss
    
    def get_components(self, student_logits: torch.Tensor,
                       teacher_logits: torch.Tensor,
                       true_actions: torch.Tensor):
        """
        Return individual loss components for logging.
        """
        # Align dimensions: use minimum size
        min_dim = min(student_logits.shape[-1], teacher_logits.shape[-1], true_actions.shape[-1])
        student_logits = student_logits[..., :min_dim]
        teacher_logits = teacher_logits[..., :min_dim]
        true_actions = true_actions[..., :min_dim]
        
        # Task loss: MSE between student and ground truth
        task_loss = F.mse_loss(student_logits, true_actions)
        
        # Distillation loss: MSE between student and teacher
        distill_loss = F.mse_loss(student_logits, teacher_logits)
        
        # Combined loss
        total_loss = self.alpha * distill_loss + (1 - self.alpha) * task_loss
        
        return total_loss, task_loss, distill_loss