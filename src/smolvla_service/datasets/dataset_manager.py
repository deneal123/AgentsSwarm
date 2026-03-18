import os
from lerobot.datasets.lerobot_dataset import LeRobotDataset
import json
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

from typing import Optional, List
from .real_dataset import RealLeRobotDataset
from torch.utils.data import DataLoader


class DatasetManager:
    
    SUPPORTED_DATASETS = [
        'lerobot/pusht',
        'lerobot/libero',
        'lerobot/aloha_static_coffee',
        'lerobot/aloha_static_fork_pick_up',
        'lerobot/aloha_static_tape_pick_up',
        'lerobot/aloha_static_rope_smooth'
    ]
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir
    
    def create_dataset(self, dataset_name: str, split: str = 'train',
                      num_samples: int = 1000, percentage: float = None):
        
        if dataset_name not in self.SUPPORTED_DATASETS:
            raise ValueError(f"Dataset {dataset_name} not supported")
        
        return RealLeRobotDataset(
            dataset_name=dataset_name,
            split=split,
            num_samples=num_samples,
            cache_dir=self.cache_dir,
            percentage=percentage
        )
    
    def create_dataloaders(self, dataset_name: str, batch_size: int = 32,
                          num_samples: int = 1000, percentage: float = None):
        
        train_dataset = self.create_dataset(dataset_name, 'train', num_samples, percentage)
        val_dataset = self.create_dataset(dataset_name, 'val', num_samples, percentage)
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=2)
        
        return train_loader, val_loader
    
    @staticmethod
    def list_available_datasets() -> List[str]:
        return DatasetManager.SUPPORTED_DATASETS.copy()


if __name__ == "__main__":
    manager = DatasetManager()
    manager.list_available_datasets()
    datasets = manager.download_sample_datasets()
    manager.save_dataset_manifest()
