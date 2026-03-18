from lerobot.datasets.lerobot_dataset import LeRobotDataset

dataset = LeRobotDataset("lerobot/pusht")

print(f"Dataset length: {len(dataset)}")
print(f"Keys in first item: {list(dataset[0].keys())}")

item = dataset[0]
for key, value in item.items():
    print(f"{key}: {type(value)}, shape: {value.shape if hasattr(value, 'shape') else 'N/A'}")