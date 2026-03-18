from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
import torch

model_id = "lerobot/smolvla_base"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Loading SmolVLA from {model_id}...")
policy = SmolVLAPolicy.from_pretrained(model_id).to(device).eval()

print(f"Loaded policy: {type(policy)}")
print(f"Parameters: {sum(p.numel() for p in policy.parameters()):,}")

preprocess, postprocess = make_pre_post_processors(
    policy.config,
    model_id,
    preprocessor_overrides={"device_processor": {"device": str(device)}},
)

print("Preprocessors loaded successfully!")
print(f"Config: {policy.config}")