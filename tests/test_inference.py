"""Test full teacher inference."""
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
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
policy = SmolVLAPolicy.from_pretrained('lerobot/smolvla_base').to(device).eval()
preprocess, postprocess = make_pre_post_processors(policy.config, 'lerobot/smolvla_base')

# Test inference
batch = preprocess(sample)
batch = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

print("Running inference...")
with torch.no_grad():
    raw_action = policy.select_action(batch)

print(f"Raw action shape: {raw_action.shape}")
print(f"Raw action: {raw_action}")

# Postprocess
action = postprocess(raw_action)
print(f"Action shape: {action.shape}")
print(f"Action: {action}")
