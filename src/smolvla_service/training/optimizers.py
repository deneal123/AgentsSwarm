import torch
import torch.nn as nn


def apply_quantization(model: nn.Module, dtype: str = 'int8'):
    if dtype == 'fp16':
        return model.half()
    
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            if dtype == 'int8' and hasattr(module, 'weight'):
                scale = module.weight.abs().max() / 127
                module.weight.data = torch.round(module.weight.data / scale) * scale
    
    return model


def apply_pruning(model: nn.Module, sparsity: float = 0.3):
    for module in model.modules():
        if isinstance(module, nn.Linear) and hasattr(module, 'weight'):
            mask = torch.rand(module.weight.shape) > sparsity
            module.weight.data *= mask.float().to(module.weight.device)
    
    return model


class OptimizationManager:
    
    def __init__(self):
        pass
    
    def analyze_model(self, model: nn.Module):
        quantizable = sum(1 for m in model.modules() if isinstance(m, nn.Linear))
        total = sum(1 for _ in model.modules())
        
        return {
            'quantizable_layers': quantizable,
            'total_layers': total,
            'total_params': sum(p.numel() for p in model.parameters()),
            'feasibility': quantizable / max(total, 1)
        }
    
    def optimize(self, model: nn.Module, quantize: bool = False, prune: float = None):
        if quantize:
            model = apply_quantization(model)
        
        if prune is not None and prune > 0:
            model = apply_pruning(model, prune)
        
        return model