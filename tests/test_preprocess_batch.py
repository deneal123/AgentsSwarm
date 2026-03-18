"""Test preprocess with batch."""
import os
os.chdir(r'C:\App\ReactProject\domains\Destil')

import torch
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors

# Load policy
device = torch.device('cpu')
policy = SmolVLAPolicy.from_pretrained('lerobot/smolvla_base').to(device).eval()
preprocess, postprocess = make_pre_post_processors(policy.config, 'lerobot/smolvla_base')

# Test with batch observation (like teacher creates)
obs_batch = {
    'observation.images.camera1': [torch.randn(3, 256, 256) for _ in range(4)],
    'observation.images.camera2': [torch.randn(3, 256, 256) for _ in range(4)],
    'observation.images.camera3': [torch.zeros(3, 256, 256) for _ in range(4)],
    'observation.state': [torch.randn(6) for _ in range(4)],
    'task': 'put the white mug on the left plate and put the yellow and white mug on the right plate',
    'task_index': 0,
}

print("Testing preprocess with batch...")
try:
    batch = preprocess(obs_batch)
    print("Success!")
    print("Keys:", batch.keys())
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
