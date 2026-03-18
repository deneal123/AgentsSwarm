"""Test preprocess directly."""
import os
os.chdir(r'C:\App\ReactProject\domains\Destil')

import torch
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.datasets.lerobot_dataset import LeRobotDataset

# Load dataset
ds = LeRobotDataset('lerobot/libero')
sample = ds[0]

# Load policy
policy = SmolVLAPolicy.from_pretrained('lerobot/smolvla_base')
preprocess, postprocess = make_pre_post_processors(policy.config, 'lerobot/smolvla_base')

# Try preprocessing
print("Sample keys:", sample.keys())
print("Sample task:", sample['task'])
print("Sample task_index:", sample['task_index'])

# Try with sample directly
try:
    batch = preprocess(sample)
    print("Preprocess succeeded!")
    print("Batch keys:", batch.keys())
except Exception as e:
    print(f"Preprocess failed: {e}")

# Try with batch format
batch_sample = {
    'observation.images.image': sample['observation.images.image'],
    'observation.images.image2': sample['observation.images.image2'],
    'observation.state': sample['observation.state'],
    'task': sample['task'],
    'task_index': sample['task_index'],
}

try:
    batch = preprocess(batch_sample)
    print("Batch preprocess succeeded!")
    print("Batch keys:", batch.keys())
except Exception as e:
    print(f"Batch preprocess failed: {e}")
