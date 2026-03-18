"""SmolVLA Optimization Framework"""

from .models import RealSmolVLAModel, StudentModel, DistillationLoss
from .training import DistillationTrainer, OptimizationManager
from .utils import ConfigManager, setup_logger, Profiler

__version__ = "v0.0.1"
__author__ = "Volkhin Danil"
