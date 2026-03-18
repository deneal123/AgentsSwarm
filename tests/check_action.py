from lerobot.datasets.lerobot_dataset import LeRobotDataset
ds = LeRobotDataset('lerobot/libero')
item = ds[0]
print('Action shape:', item['action'].shape)
print('Action:', item['action'])
