"""Test teacher inference with real data from LIBERO dataset."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from src.models.teacher import RealSmolVLAModel
from src.datasets.real_dataset import RealLeRobotDataset, collate_fn
from torch.utils.data import DataLoader


def test_teacher_with_libero():
    print("Loading LIBERO dataset...")
    dataset = RealLeRobotDataset(
        dataset_name='lerobot/libero',
        split='train',
        num_samples=100,
    )
    
    print(f"Dataset length: {len(dataset)}")
    print(f"Camera keys: {dataset.camera_keys}")
    print(f"State dim: {dataset.state_dim}")
    print(f"Action dim: {dataset.action_dim}")
    
    # Get a batch with task info
    loader = DataLoader(dataset, batch_size=4, shuffle=False, collate_fn=collate_fn)
    batch = next(iter(loader))
    
    # Extract data from batch (new format with dict)
    if isinstance(batch, dict):
        images = batch.get('images')
        state = batch.get('state')
        action = batch.get('action')
        task = batch.get('task')
        task_index = batch.get('task_index')
    else:
        images, state, action, task, task_index = batch
    
    print(f"\nBatch shapes:")
    print(f"  images: {images.shape}")
    print(f"  state: {state.shape}")
    print(f"  action: {action.shape}")
    print(f"  task: {task}")
    print(f"  task_index: {task_index}")
    
    # Load teacher
    print("\nLoading teacher model...")
    teacher = RealSmolVLAModel(model_id='lerobot/smolvla_base')
    
    # Test inference with task info
    print("\nTesting teacher inference...")
    with torch.no_grad():
        output = teacher(images, state, task=task, task_index=task_index)
    
    print(f"Teacher output shape: {output.shape}")
    print(f"Teacher output sample: {output[0][:3]}")
    
    print("\n✓ Teacher inference works!")


if __name__ == '__main__':
    test_teacher_with_libero()
