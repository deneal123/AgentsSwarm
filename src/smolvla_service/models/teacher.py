import torch
import torch.nn as nn
from typing import Dict, Any, Optional

from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors


class RealSmolVLAModel(nn.Module):
    """
    Real SmolVLA model loaded from HuggingFace via LeRobot.
    
    This is the actual pre-trained SmolVLA model that will be used as teacher.
    Uses proper preprocessing pipeline: preprocess -> select_action -> postprocess.
    """
    
    def __init__(self, model_id: str = 'lerobot/smolvla_base', action_dim: int = 7, device=None):
        super().__init__()
        self.model_id = model_id
        self.action_dim = action_dim
        
        # Use provided device or default to cuda if available
        self.device = device if device is not None else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Loading SmolVLA from {model_id} on {self.device}...")
        self.policy = SmolVLAPolicy.from_pretrained(model_id).to(self.device).eval()
        print(f"SmolVLA loaded: {sum(p.numel() for p in self.policy.parameters()):,} parameters")
        
        # Load preprocessors
        self.preprocess, self.postprocess = make_pre_post_processors(
            self.policy.config,
            model_id,
            preprocessor_overrides={"device_processor": {"device": str(self.device)}},
        )
        print("Preprocessors loaded")
        
        # Freeze all parameters - teacher is in inference mode only
        for param in self.policy.parameters():
            param.requires_grad = False
        
        self.num_parameters = sum(p.numel() for p in self.policy.parameters())
    
        # Get expected observation keys from config
        self._setup_observation_keys()
    
    def _setup_observation_keys(self):
        """Extract observation keys from policy config."""
        config = self.policy.config
        self.observation_keys = {}
        
        # Camera observation keys
        if hasattr(config, 'cameras') and config.cameras:
            self.observation_keys['cameras'] = list(config.cameras.keys()) if isinstance(config.cameras, dict) else config.cameras
        else:
            # Default LeRobot camera keys
            self.observation_keys['cameras'] = ['image', 'image2']
        
        # State observation key
        self.observation_keys['state'] = getattr(config, 'state_key', 'observation.state')
        
        # Action key
        self.observation_keys['action'] = 'action'
    
    def _prepare_batch_for_smolvla(self, images: torch.Tensor, state: torch.Tensor, task=None, task_index=None) -> Dict[str, Any]:
        """
        Prepare batch in LeRobot format for SmolVLA.
        
        Handles format conversion from LIBERO (2 cameras, 8-dim state) to 
        SmolVLA (3 cameras, 6-dim state).
        
        Args:
            images: Concatenated multi-view images [batch, num_cameras*3, H, W]
            state: Robot state [batch, state_dim]
            task: Optional task description string
            task_index: Optional task index tensor
        
        Returns:
            Dictionary in LeRobot observation format with camera1/camera2/camera3 keys
        """
        device = images.device if images is not None else state.device
        batch_size = images.shape[0] if images is not None else state.shape[0]
        
        # SmolVLA expects 3 cameras: camera1, camera2, camera3 (NOT image/image2)
        smolvla_cameras = ['camera1', 'camera2', 'camera3']
        
        # Determine how many cameras we have in the input
        num_input_cameras = images.shape[1] // 3 if images is not None else 0
        
        observation = {}
        
        # Handle multi-view cameras - map to camera1/camera2/camera3
        if images is not None:
            for i in range(min(num_input_cameras, 3)):
                cam_img = images[:, i * 3:(i + 1) * 3, :, :]  # [batch, 3, H, W]
                cam_name = smolvla_cameras[i]
                
                if batch_size == 1:
                    observation[f'observation.images.{cam_name}'] = cam_img[0]
                else:
                    observation[f'observation.images.{cam_name}'] = [cam_img[j] for j in range(batch_size)]
            
            # Handle missing cameras - fill with zeros (SmolVLA expects 3 cameras)
            for i in range(num_input_cameras, 3):
                cam_name = smolvla_cameras[i]
                if batch_size == 1:
                    observation[f'observation.images.{cam_name}'] = torch.zeros(3, 256, 256, device=device, dtype=torch.float32)
                else:
                    observation[f'observation.images.{cam_name}'] = [torch.zeros(3, 256, 256, device=device, dtype=torch.float32) for _ in range(batch_size)]
        else:
            for cam_name in smolvla_cameras:
                if batch_size == 1:
                    observation[f'observation.images.{cam_name}'] = torch.zeros(3, 256, 256, device=device, dtype=torch.float32)
                else:
                    observation[f'observation.images.{cam_name}'] = [torch.zeros(3, 256, 256, device=device, dtype=torch.float32) for _ in range(batch_size)]
        
        # Handle state - SmolVLA expects 6-dim state, LIBERO has 8-dim
        if state is not None:
            state_list = []
            for j in range(batch_size):
                s = state[j]
                if s.shape[-1] > 6:
                    s = s[:6]  # Truncate to 6
                elif s.shape[-1] < 6:
                    s = torch.cat([s, torch.zeros(6 - s.shape[-1], device=device)])
                state_list.append(s)
            
            if batch_size == 1:
                observation['observation.state'] = state_list[0]
            else:
                observation['observation.state'] = state_list
        else:
            if batch_size == 1:
                observation['observation.state'] = torch.zeros(6, device=device, dtype=torch.float32)
            else:
                observation['observation.state'] = [torch.zeros(6, device=device, dtype=torch.float32) for _ in range(batch_size)]
        
        # Add task info (required by LeRobot preprocessing)
        # task must be a string, task_index must be an int
        if task is not None and isinstance(task, str):
            observation['task'] = task
        
        # Extract scalar from task_index if it's a tensor
        if task_index is not None:
            if isinstance(task_index, torch.Tensor):
                # If batched, take first element
                if task_index.numel() > 1:
                    task_index = task_index[0]
                task_index = task_index.item()
            observation['task_index'] = int(task_index)
        
        return observation
    
    def forward(self, images: torch.Tensor, state: torch.Tensor = None, task=None, task_index=None) -> torch.Tensor:
        """
        Forward pass through real SmolVLA teacher.
        
        Note: SmolVLA preprocess() only works with single observations, not batches.
        We process each sample individually.
        
        Args:
            images: Multi-view images [batch, num_cameras*3, H, W]
            state: Robot state [batch, state_dim]
            task: Optional task description string (shared for batch)
            task_index: Optional task index
        
        Returns:
            Predicted actions [batch, action_dim]
        """
        device = images.device if images is not None else (state.device if state is not None else self.device)
        
        # Ensure batch dimension
        if images is not None and images.dim() == 3:
            images = images.unsqueeze(0)
        if state is not None and state.dim() == 1:
            state = state.unsqueeze(0)
        
        batch_size = images.shape[0] if images is not None else state.shape[0]
        
        # Get action dimension from config
        action_dim = getattr(self.policy.config, 'action_dim', self.action_dim)
        
        # Process each sample individually (preprocess doesn't support batching)
        all_actions = []
        
        # Use policy device (teacher is already on correct device)
        policy_device = next(self.policy.parameters()).device
        
        for i in range(batch_size):
            # Extract single sample and move to policy device
            img_i = images[i].to(policy_device) if images is not None else None
            state_i = state[i].to(policy_device) if state is not None else None
            
            # Prepare observation for single sample (all on same device as policy)
            # SmolVLA will handle state dimension internally
            observation = {
                'observation.images.camera1': img_i[:3] if img_i is not None else torch.zeros(3, 256, 256, device=policy_device, dtype=torch.float32),
                'observation.images.camera2': img_i[3:6] if img_i is not None and img_i.shape[0] > 3 else torch.zeros(3, 256, 256, device=policy_device, dtype=torch.float32),
                'observation.images.camera3': torch.zeros(3, 256, 256, device=policy_device, dtype=torch.float32),
                'observation.state': state_i if state_i is not None else torch.zeros(8, device=policy_device, dtype=torch.float32),  # Use full state
                'task': task if task else '',
                'task_index': task_index if task_index is not None else 0,
            }
            
            try:
                # Preprocess single sample
                batch = self.preprocess(observation)
                # Move all tensors to policy device
                batch = {k: v.to(policy_device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
                
                # Get teacher prediction
                with torch.no_grad():
                    raw_action = self.policy.select_action(batch)
                
                # Postprocess
                action = self.postprocess(raw_action)
                
                # Ensure 1D output
                if action.dim() > 1:
                    action = action.squeeze()
                
                all_actions.append(action)
                
            except Exception as e:
                print(f"Warning: SmolVLA inference failed for sample {i}: {e}")
                all_actions.append(torch.zeros(action_dim, device=policy_device))
        
        # Stack all actions and ensure they're on policy device
        try:
            actions = torch.stack(all_actions)
            # Explicitly move to policy device
            actions = actions.to(policy_device)
        except:
            # Handle case where actions are 0D scalars
            actions = torch.tensor([a.item() if hasattr(a, 'item') else a for a in all_actions], device=policy_device)
        
        return actions
    
    def get_num_parameters(self) -> int:
        """Return total number of parameters."""
        return self.num_parameters
    
    @property
    def config(self):
        """Return policy config."""
        return self.policy.config
    
    def get_action_dim(self) -> int:
        """Get action dimension from policy config."""
        return getattr(self.policy.config, 'action_dim', self.action_dim)