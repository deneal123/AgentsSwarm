from lerobot.datasets.lerobot_dataset import LeRobotDataset

try:
    dataset = LeRobotDataset("lerobot/libero")
    print(f"Dataset length: {len(dataset)}")
    print(f"Keys in first item: {list(dataset[0].keys())}")
    
    item = dataset[0]
    for key, value in item.items():
        if 'image' in key or 'state' in key or 'action' in key:
            print(f"{key}: {type(value)}, shape: {value.shape if hasattr(value, 'shape') else 'N/A'}")
except Exception as e:
    print(f"Error: {e}")