"""
Paddy Farming Assistant - Model Loader
Responsible for loading model architectures and existing checkpoints.
Preserves compatibility with the trained EfficientNet-B4 model on CPU.
"""

import logging
from pathlib import Path
from typing import Optional, Any
from app import config

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Manages loading, caching, and accessing trained AI models.
    Supports CPU-only inference for machines without dedicated GPU.
    """

    _instance: Optional["ModelLoader"] = None
    _efficientnet_model: Optional[Any] = None
    _load_status: str = "not_loaded"
    _last_error: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_device(cls) -> str:
        """
        Returns torch device string (defaults to cpu).
        """
        return config.DEVICE

    @classmethod
    def get_model_status(cls) -> str:
        """
        Returns the in-memory loading status of the model:
        - 'loaded': Model weights are loaded and ready in memory.
        - 'not_loaded': Model has not been loaded into memory yet.
        - 'failed': A previous attempt to load the model failed.
        """
        if cls._efficientnet_model is not None:
            return "loaded"
        if cls._load_status == "failed":
            return "failed"
        return "not_loaded"

    @classmethod
    def is_model_loaded(cls) -> bool:
        """
        Returns True if the model is currently resident in memory.
        """
        return cls._efficientnet_model is not None

    @classmethod
    def get_model(cls):
        """
        Retrieves the cached EfficientNet-B4 model, loading it into memory if not yet loaded.
        Ensures a failed load never falls back to random weights.
        """
        if cls._efficientnet_model is None:
            return cls.load_efficientnet_b4()
        return cls._efficientnet_model


    @classmethod
    def build_efficientnet_b4_architecture(cls, num_classes: int = config.NUM_CLASSES):
        """
        Constructs the exact EfficientNet-B4 architecture matching STEP 4A / 4D:
        - Backbone: torchvision.models.efficientnet_b4
        - Custom Classifier Head:
            Linear(1792, 512) -> ReLU -> Dropout(0.4) -> Linear(512, num_classes)
        """
        try:
            import torch.nn as nn
            from torchvision.models import efficientnet_b4
        except ImportError:
            logger.warning("PyTorch / Torchvision not yet installed in current environment.")
            return None

        model = efficientnet_b4(weights=None)
        model.classifier = nn.Sequential(
            nn.Linear(1792, 512),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(512, num_classes),
        )
        return model

    @classmethod
    def load_efficientnet_b4(cls, checkpoint_path: Optional[Path] = None):
        """
        Loads the trained EfficientNet-B4 weights onto CPU.
        Uses torch.load with map_location='cpu'.
        """
        target_path = checkpoint_path or config.EFFICIENTNET_CHECKPOINT_PATH

        if checkpoint_path is None and cls._efficientnet_model is not None:
            return cls._efficientnet_model

        if not target_path.exists():
            cls._load_status = "failed"
            cls._last_error = f"Checkpoint not found at: {target_path}"
            logger.error("Checkpoint not found at: %s", target_path)
            raise FileNotFoundError(
                "Checkpoint file does not exist on disk."
            )

        try:
            import torch
        except ImportError as e:
            cls._load_status = "failed"
            cls._last_error = str(e)
            logger.error("PyTorch import error: %s", e)
            raise ImportError(
                "PyTorch is required for model loading. "
                "Install backend dependencies before running inference."
            )

        try:
            logger.info("Loading EfficientNet-B4 from %s on %s...", target_path, config.DEVICE)
            model = cls.build_efficientnet_b4_architecture(config.NUM_CLASSES)
            
            # Load state dict strictly mapped to CPU
            checkpoint = torch.load(target_path, map_location=torch.device(config.DEVICE))
            
            if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
                state_dict = checkpoint["state_dict"]
            elif isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
            else:
                state_dict = checkpoint

            model.load_state_dict(state_dict)
            model.to(config.DEVICE)
            model.eval()

            cls._efficientnet_model = model
            cls._load_status = "loaded"
            cls._last_error = None
            logger.info("EfficientNet-B4 loaded successfully onto %s.", config.DEVICE)
            return cls._efficientnet_model
        except Exception as e:
            cls._load_status = "failed"
            cls._last_error = str(e)
            logger.error("Failed to load EfficientNet-B4 model: %s", e, exc_info=True)
            raise

