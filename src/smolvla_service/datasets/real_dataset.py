import torch
from torch.utils.data import Dataset
import numpy as np
import os
from typing import Optional


class RealLeRobotDataset(Dataset):
    """
    LeRobot dataset with multi-view camera support.
    
    Supports datasets like lerobot/libero with multi-view cameras.
    """
    
    def __init__(self, dataset_name: str, split: str = 'train', num_samples: int = 1000, 
                 cache_dir: str = None, percentage: float = None):
        self.dataset_name = dataset_name
        self.split = split
        self.num_samples = num_samples
        
        self.dataset = self._load_dataset(dataset_name, cache_dir)
        
        if self.dataset is not None:
            total = len(self.dataset)
            limit = min(total, num_samples)
            
            if percentage is not None:
                limit = int(total * percentage)
            
            split_idx = int(limit * 0.8)
            
            if split == 'train':
                self.indices = list(range(0, split_idx))
            else:
                self.indices = list(range(split_idx, limit))
            
            if len(self.indices) == 0:
                self.indices = [0] if split == 'train' else []
                
            # Determine dataset structure
            self._analyze_dataset_structure()
        else:
            self._create_fallback_data()
    
    def _load_dataset(self, dataset_name: str, cache_dir: str):
        os.environ.setdefault('HF_DATASETS_CACHE', 
                             cache_dir or os.path.expanduser('~/.cache/huggingface/datasets'))
        
        try:
            from lerobot.datasets.lerobot_dataset import LeRobotDataset
            return LeRobotDataset(dataset_name)
        except Exception as e:
            print(f"Failed to load dataset {dataset_name}: {e}")
            return None
    
    def _analyze_dataset_structure(self):
        """Analyze the dataset structure to understand input format."""
        if len(self.dataset) == 0:
            return
            
        item = self.dataset[0]
        
        # Check for multi-view cameras
        self.camera_keys = []
        for key in item.keys():
            if 'image' in key.lower() and 'observation' in key:
                self.camera_keys.append(key)
        
        # Sort camera keys
        self.camera_keys.sort()
        
        # Check state
        self.state_key = None
        for key in item.keys():
            if 'state' in key.lower() and 'observation' in key:
                self.state_key = key
                break
        
        # Determine shapes
        if self.camera_keys:
            self.image_shape = item[self.camera_keys[0]].shape
        if self.state_key:
            self.state_dim = item[self.state_key].shape[-1]
        if 'action' in item:
            self.action_dim = item['action'].shape[-1]
        
        print(f"Dataset structure:")
        print(f"  Cameras: {self.camera_keys}, shape: {self.image_shape}")
        print(f"  State: {self.state_key}, dim: {self.state_dim}")
        print(f"  Action: dim: {self.action_dim}")
    
    def _create_fallback_data(self):
        """Create synthetic data for testing."""
        np.random.seed(42 if self.split == 'train' else 123)
        self.data = []
        
        # Default to libero-style structure
        self.camera_keys = ['observation.images.image', 'observation.images.image2']
        self.image_shape = (3, 256, 256)
        self.state_dim = 8
        self.action_dim = 7
        
        prev_action = np.zeros(7)
        
        for i in range(self.num_samples):
            # Multi-view images
            img1 = np.random.randn(3, 256, 256).astype(np.float32)
            img2 = np.random.randn(3, 256, 256).astype(np.float32)
            
            state = np.random.uniform(-1, 1, 8).astype(np.float32)
            action = np.random.uniform(-1, 1, 7).astype(np.float32)
            
            if i > 0:
                action = 0.7 * action + 0.3 * prev_action
            
            prev_action = action.copy()
            
            self.data.append({
                'img1': img1,
                'img2': img2,
                'state': state,
                'action': action
            })
    
    def __len__(self):
        if self.dataset is not None:
            return len(self.indices)
        return len(self.data)
    
    def __getitem__(self, idx):
        if self.dataset is not None:
            return self._get_real_item(idx)
        return self._get_fallback_item(idx)
    
    def _get_real_item(self, idx):
        """Get real item from dataset."""
        actual_idx = self.indices[idx]
        item = self.dataset[actual_idx]
        
        # Concatenate multi-view images
        if self.camera_keys:
            images = []
            for cam_key in self.camera_keys:
                img = item[cam_key]
                if len(img.shape) == 3:  # [C, H, W]
                    images.append(img)
                elif len(img.shape) == 4:  # [T, C, H, W] - take first frame
                    images.append(img[0])
            
            # Stack images: [num_cameras*3, H, W]
            images = torch.cat(images, dim=0)
        else:
            images = item.get('observation.image', torch.zeros(3, 256, 256))
        
        # Get state
        if self.state_key:
            state = item[self.state_key]
        else:
            state = torch.zeros(self.state_dim)
        
        # Get action
        action = item['action']
        
        # Get task info (required for SmolVLA)
        task = item.get('task', '')
        task_index = item.get('task_index', torch.tensor(0))
        
        # Return as dict for batch collation
        return {
            'images': images.float(),
            'state': state.float(),
            'action': action.float(),
            'task': task,
            'task_index': task_index
        }
    
    def _get_fallback_item(self, idx):
        """Get synthetic item for testing."""
        item = self.data[idx % len(self.data)]
        
        # Add noise for augmentation
        img1_noise = np.random.normal(0, 0.05, item['img1'].shape).astype(np.float32)
        img2_noise = np.random.normal(0, 0.05, item['img2'].shape).astype(np.float32)
        action_noise = np.random.normal(0, 0.01, item['action'].shape).astype(np.float32)
        
        # Concatenate images
        images = np.concatenate([item['img1'] + img1_noise, item['img2'] + img2_noise], axis=0)
        
        return (
            torch.from_numpy(images),
            torch.from_numpy(item['state']),
            torch.from_numpy(item['action'] + action_noise)
        )


def collate_fn(batch):
    """Collate function for handling dict-style samples."""
    images = torch.stack([item['images'] for item in batch])
    states = torch.stack([item['state'] for item in batch])
    actions = torch.stack([item['action'] for item in batch])
    
    # Handle task (string) - take first in batch
    tasks = [item['task'] for item in batch] if 'task' in batch[0] else [''] * len(batch)
    
    # Take first task as single string (SmolVLA expects single string, not list)
    task_str = tasks[0] if tasks else ''
    
    # Handle task_index - take first value as scalar int
    task_idx = 0
    if 'task_index' in batch[0]:
        first_idx = batch[0]['task_index']
        # Extract scalar
        if hasattr(first_idx, 'item'):
            task_idx = first_idx.item()
        elif hasattr(first_idx, 'cpu'):
            task_idx = first_idx.cpu().item()
        else:
            task_idx = int(first_idx)
    
    return {
        'images': images,
        'state': states,
        'action': actions,
        'task': task_str,
        'task_index': task_idx
    }


def create_dataloader(dataset: Dataset, batch_size: int = 32, shuffle: bool = True, num_workers: int = 2):
    return torch.utils.data.DataLoader(
        dataset, 
        batch_size=batch_size, 
        shuffle=shuffle, 
        num_workers=num_workers,
        pin_memory=True,
        collate_fn=collate_fn
    )