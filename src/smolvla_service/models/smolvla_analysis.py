import torch
import torch.nn as nn
from typing import Dict, List, Tuple


class ModelAnalyzer:
    
    @staticmethod
    def count_parameters(model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters())
    
    @staticmethod
    def count_trainable_parameters(model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    @staticmethod
    def get_layer_sizes(model: nn.Module) -> List[Tuple[str, int]]:
        layers = []
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                layers.append((name, module.out_features))
        return layers
    
    @staticmethod
    def analyze_model(model: nn.Module) -> Dict:
        return {
            'total_params': ModelAnalyzer.count_parameters(model),
            'trainable_params': ModelAnalyzer.count_trainable_parameters(model),
            'layers': ModelAnalyzer.get_layer_sizes(model)
        }


class CompressionMetrics:
    
    @staticmethod
    def compute_compression_ratio(teacher_params: int, student_params: int) -> float:
        return teacher_params / student_params
    
    @staticmethod
    def compute_size_reduction(teacher_params: int, student_params: int) -> float:
        return (1 - student_params / teacher_params) * 100


def analyze_distillation(student: nn.Module, teacher: nn.Module, 
                         dataloader, device: torch.device) -> Dict:
    teacher.eval()
    student.eval()
    
    teacher_params = ModelAnalyzer.count_parameters(teacher)
    student_params = ModelAnalyzer.count_parameters(student)
    
    compression = CompressionMetrics.compute_compression_ratio(teacher_params, student_params)
    reduction = CompressionMetrics.compute_size_reduction(teacher_params, student_params)
    
    return {
        'teacher_params': teacher_params,
        'student_params': student_params,
        'compression_ratio': compression,
        'size_reduction_percent': reduction
    }
