"""Test preprocess with different formats."""
import os
os.chdir(r'C:\App\ReactProject\domains\Destil')

import torch
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors

# Load policy
device = torch.device('cpu')
policy = SmolVLAPolicy.from_pretrained('lerobot/smolvla_base').to(device).eval()
preprocess, postprocess = make_pre_post_processors(policy.config, 'lerobot/smolvla_base')

# Test with single observation
obs_single = {
    'observation.images.camera1': torch.randn(3, 256, 256),
    'observation.images.camera2': torch.randn(3, 256, 256),
    'observation.images.camera3': torch.zeros(3, 256, 256),
    'observation.state': torch.randn(6),
    'task': 'put the white mug on the left plate',
    'task_index': 0,
}

print("Test 1: Single observation...")
try:
    batch = preprocess(obs_single)
    print("Success! Keys:", list(batch.keys())[:5])
except Exception as e:
    print(f"Failed: {e}")

# Test with batch in list form
obs_list = {
    'observation.images.camera1': [torch.randn(3, 256, 256) for _ in range(4)],
    'observation.images.camera2': [torch.randn(3, 256, 256) for _ in range(4)],
    'observation.images.camera3': [torch.zeros(3, 256, 256) for _ in range(4)],
    'observation.state': [torch.randn(6) for _ in range(4)],
    'task': ['put the white mug on the left plate'] * 4,  # List!
    'task_index': [0] * 4,  # List!
}

print("\nTest 2: Batch with lists...")
try:
    batch = preprocess(obs_list)
    print("Success! Keys:", list(batch.keys())[:5])
except Exception as e:
    print(f"Failed: {e}")
