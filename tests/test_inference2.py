"""Test inference with camera mapping."""
import os
os.chdir(r'C:\App\ReactProject\domains\Destil')

import torch
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.datasets.lerobot_dataset import LeRobotDataset

# Load dataset
ds = LeRobotDataset('lerobot/libero')
sample = ds[0]

# Map LIBERO cameras to SmolVLA cameras
observation = {
    'observation.images.camera1': sample['observation.images.image'],
    'observation.images.camera2': sample['observation.images.image2'],
    'observation.images.camera3': torch.zeros(3, 256, 256),  # Add dummy third camera
    'observation.state': sample['observation.state'][:6],  # Truncate to 6
    'task': sample['task'],
    'task_index': sample['task_index'],
}

# Load policy
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
policy = SmolVLAPolicy.from_pretrained('lerobot/smolvla_base').to(device).eval()
preprocess, postprocess = make_pre_post_processors(policy.config, 'lerobot/smolvla_base')

# Test inference
batch = preprocess(observation)
batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

print("Running inference...")
with torch.no_grad():
    raw_action = policy.select_action(batch)

print(f"Raw action shape: {raw_action.shape}")

# Postprocess
action = postprocess(raw_action)
print(f"Action shape: {action.shape}")
print(f"Action: {action}")
