"""Debug teacher inference."""
import os
os.chdir(r'C:\App\ReactProject\domains\Destil')

import torch
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from torch.utils.data import DataLoader
from src.datasets.real_dataset import collate_fn

# Load dataset
ds = LeRobotDataset('lerobot/libero')

# Create simple wrapper to get task
class DebugDataset:
    def __init__(self, dataset):
        self.dataset = dataset
    def __len__(self):
        return len(self.dataset)
    def __getitem__(self, idx):
        item = self.dataset[idx]
        return {
            'images': torch.cat([item['observation.images.image'], item['observation.images.image2']], dim=0),
            'state': item['observation.state'][:6],  # Truncate to 6
            'action': item['action'],
            'task': item['task'],
            'task_index': item['task_index']
        }

debug_ds = DebugDataset(ds)
loader = DataLoader(debug_ds, batch_size=2, collate_fn=collate_fn)
batch = next(iter(loader))

print("Batch keys:", batch.keys())
print("Task:", batch['task'], type(batch['task']))
print("Task index:", batch['task_index'], type(batch['task_index']))

# Load policy
device = torch.device('cpu')
policy = SmolVLAPolicy.from_pretrained('lerobot/smolvla_base').to(device).eval()
preprocess, postprocess = make_pre_post_processors(policy.config, 'lerobot/smolvla_base')

# Prepare observation - single sample
obs_single = {
    'observation.images.camera1': batch['images'][0, :3],
    'observation.images.camera2': batch['images'][0, 3:6],
    'observation.images.camera3': torch.zeros(3, 256, 256),
    'observation.state': batch['state'][0],
    'task': batch['task'],  # String
    'task_index': batch['task_index'],
}

print("\nObservation task:", obs_single['task'], type(obs_single['task']))
print("Observation task_index:", obs_single['task_index'])

# Test preprocess
try:
    processed = preprocess(obs_single)
    print("Preprocess succeeded!")
    print("Processed keys:", processed.keys())
except Exception as e:
    print(f"Preprocess failed: {e}")
