"""Debug teacher forward."""
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

class DebugDataset:
    def __init__(self, dataset):
        self.dataset = dataset
    def __len__(self):
        return len(self.dataset)
    def __getitem__(self, idx):
        item = self.dataset[idx]
        return {
            'images': torch.cat([item['observation.images.image'], item['observation.images.image2']], dim=0),
            'state': item['observation.state'][:6],
            'action': item['action'],
            'task': item['task'],
            'task_index': item['task_index']
        }

debug_ds = DebugDataset(ds)
loader = DataLoader(debug_ds, batch_size=2, collate_fn=collate_fn)
batch = next(iter(loader))

# Load policy
device = torch.device('cpu')
policy = SmolVLAPolicy.from_pretrained('lerobot/smolvla_base').to(device).eval()
preprocess, postprocess = make_pre_post_processors(policy.config, 'lerobot/smolvla_base')

# Test teacher forward manually
images = batch['images']
state = batch['state']
task = batch['task']
task_index = batch['task_index']

print(f"images shape: {images.shape}")
print(f"state shape: {state.shape}")
print(f"task: {task}")
print(f"task_index: {task_index}")

# Prepare observation - exactly as teacher does
obs = {
    'observation.images.camera1': images[0, :3],
    'observation.images.camera2': images[0, 3:6],
    'observation.images.camera3': torch.zeros(3, 256, 256),
    'observation.state': state[0],
    'task': task,
    'task_index': task_index,
}

print("\nObservation task:", obs['task'], type(obs['task']))
print("Observation task_index:", obs['task_index'], type(obs['task_index']))

# Test preprocess
try:
    processed = preprocess(obs)
    print("\nPreprocess succeeded!")
    print("Processed task:", processed.get('task'))
    print("Processed task_index:", processed.get('task_index'))
except Exception as e:
    print(f"\nPreprocess failed: {e}")
    import traceback
    traceback.print_exc()
