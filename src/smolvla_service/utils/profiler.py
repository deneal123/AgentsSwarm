import torch
import time
from typing import Dict


class Profiler:
    
    def __init__(self, model: torch.nn.Module, device: torch.device):
        self.model = model
        self.device = device
    
    def measure_latency(self, input_shape: tuple = (1, 2048), num_runs: int = 100) -> Dict[str, float]:
        self.model.eval()
        
        dummy_input = torch.randn(*input_shape).to(self.device)
        
        for _ in range(10):
            with torch.no_grad():
                _ = self.model(dummy_input)
        
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        
        latencies = []
        for _ in range(num_runs):
            start = time.perf_counter()
            with torch.no_grad():
                _ = self.model(dummy_input)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            latencies.append((time.perf_counter() - start) * 1000)
        
        return {
            'mean_ms': sum(latencies) / len(latencies),
            'min_ms': min(latencies),
            'max_ms': max(latencies)
        }
    
    def measure_throughput(self, input_shape: tuple = (1, 2048), duration: int = 10) -> Dict[str, float]:
        self.model.eval()
        
        dummy_input = torch.randn(*input_shape).to(self.device)
        count = 0
        start = time.time()
        
        while time.time() - start < duration:
            with torch.no_grad():
                _ = self.model(dummy_input)
            count += 1
        
        return {
            'inferences_per_second': count / duration,
            'total_inferences': count
        }
