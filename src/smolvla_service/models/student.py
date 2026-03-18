import torch
import torch.nn as nn


class StudentModel(nn.Module):
    """
    Student model for knowledge distillation.
    
    Architecture matches SmolVLA teacher but with scaled dimensions:
    - Same activation (GELU)
    - Same dropout
    - Same layer structure
    - Scaled hidden dimensions, heads, and layers
    
    Input: Multi-view images (2 cameras, 256x256x3) + state (6 or 8-dim)
    Output: Actions (6-dim to match teacher)
    """
    
    def __init__(self, ratio: float = 0.5, action_dim: int = 6, num_cameras: int = 2, state_dim: int = 6):
        super().__init__()
        self.action_dim = action_dim  # Should match teacher (6)
        self.num_cameras = num_cameras
        self.state_dim = state_dim  # SmolVLA expects 6-dim state
        
        # Scale dimensions but keep minimum values
        hidden = max(int(512 * ratio), 64)  # Minimum 64
        hidden_1 = max(int(hidden * 2), 128)  # Minimum 128
        hidden_2 = max(int(hidden * 1.5), 96)  # Minimum 96
        
        # Image encoder (simplified CNN for each camera)
        # Input: 2 cameras x [3, 256, 256] -> concatenate -> [6, 256, 256]
        self.image_encoder = nn.Sequential(
            nn.Conv2d(3 * num_cameras, 64, kernel_size=7, stride=2, padding=3),
            nn.GELU(),
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(64, 128, kernel_size=5, stride=2, padding=2),
            nn.GELU(),
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.GELU(),
            nn.AdaptiveAvgPool2d((1, 1)),  # Global pooling
            nn.Flatten(),
            nn.Linear(256, hidden_1),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_1, hidden_2),
            nn.GELU(),
            nn.Dropout(0.1),
        )
        
        # State encoder (6-dim state from SmolVLA)
        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.GELU(),
            nn.Dropout(0.1),
        )
        
        # Combined features dimension
        combined_dim = hidden_2 + hidden
        
        # Feature fusion
        self.feature_fusion = nn.Sequential(
            nn.Linear(combined_dim, hidden),
            nn.GELU(),
            nn.LayerNorm(hidden)
        )
        
        # Action head (7-dim action for libero)
        self.action_head = nn.Linear(hidden, action_dim)
    
    def forward(self, images: torch.Tensor, state: torch.Tensor = None) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            images: Multi-view images [batch, num_cameras*3, H, W] or [batch, 3, H, W] for single camera
            state: Robot state [batch, 8]
        
        Returns:
            Predicted actions [batch, action_dim]
        """
        # Encode images
        img_features = self.image_encoder(images)
        
        # Encode state
        if state is not None:
            state_features = self.state_encoder(state)
            # Combine features
            combined = torch.cat([img_features, state_features], dim=-1)
        else:
            combined = img_features
        
        # Fuse features
        features = self.feature_fusion(combined)
        
        # Predict actions
        return self.action_head(features)
    
    def get_features(self, images: torch.Tensor, state: torch.Tensor = None) -> torch.Tensor:
        """Extract features without action prediction."""
        img_features = self.image_encoder(images)
        
        if state is not None:
            state_features = self.state_encoder(state)
            combined = torch.cat([img_features, state_features], dim=-1)
        else:
            combined = img_features
        
        return self.feature_fusion(combined)
    
    def get_num_parameters(self) -> int:
        """Return total number of parameters."""
        return sum(p.numel() for p in self.parameters())
