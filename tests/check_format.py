"""Check LeRobot dataset sample format."""
import os
os.chdir(r'C:\App\ReactProject\domains\Destil')

from lerobot.datasets.lerobot_dataset import LeRobotDataset

# Load a sample to see the format
ds = LeRobotDataset('lerobot/libero')
sample = ds[0]

with open('sample_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Keys: {sample.keys()}\n\n")
    for k, v in sample.items():
        if hasattr(v, 'shape'):
            f.write(f"{k}: {type(v)}, shape={v.shape}\n")
        else:
            f.write(f"{k}: {type(v)}, value={v}\n")

print("Done - see sample_output.txt")
