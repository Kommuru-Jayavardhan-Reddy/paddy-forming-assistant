"""
Paddy Farming Assistant - Multimodal Model Architecture and Loader (STEP 11D.3)
Defines the Temporal Cross-Attention Multimodal model and manages checkpoint loading.
Compatible with the trained Controlled Step 7L model (step7L_controlled_best.pth) on CPU.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

import torch
import torch.nn as nn

from app import config

logger = logging.getLogger(__name__)


class TemporalCrossAttentionModel(nn.Module):
    """
    Multimodal Paddy Disease Classifier fusing EfficientNet-B4 image embeddings
    with temporal Sentinel-2 satellite time-series (10 timesteps x 3 features).
    Architecture matches Step 7L / Step 9 exactly.
    """

    def __init__(
        self,
        image_dim: int = 1792,
        hidden_dim: int = 128,
        attention_dim: int = 256,
        num_heads: int = 8,
        num_classes: int = 11,
    ):
        super().__init__()

        # 1. Image Feature Projection
        self.image_projection = nn.Sequential(
            nn.Linear(image_dim, attention_dim),
            nn.LayerNorm(attention_dim),
            nn.GELU(),
            nn.Dropout(0.2),
        )

        # 2. Satellite Temporal Branch (Bidirectional LSTM)
        self.satellite_lstm = nn.LSTM(
            input_size=3,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            dropout=0.2,
            bidirectional=True,
        )

        self.satellite_projection = nn.Sequential(
            nn.Linear(hidden_dim * 2, attention_dim),
            nn.LayerNorm(attention_dim),
            nn.GELU(),
            nn.Dropout(0.15),
        )

        # 3. Residual Cross-Attention
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=attention_dim,
            num_heads=num_heads,
            dropout=0.1,
            batch_first=True,
        )

        self.attention_norm = nn.LayerNorm(attention_dim)

        # 4. Multimodal Fusion Network
        self.fusion = nn.Sequential(
            nn.Linear(512, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(0.4),
            nn.Linear(256, 128),
            nn.GELU(),
            nn.Dropout(0.25),
        )

        # 5. Disease Classifier Head
        self.classifier = nn.Linear(128, num_classes)

    def forward(
        self, image: torch.Tensor, satellite: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        Args:
            image: [batch_size, 1792] - EfficientNet-B4 feature embedding
            satellite: [batch_size, 10, 3] - Normalized Sentinel-2 temporal sequence
        Returns:
            logits: [batch_size, 11]
            attention: [batch_size, 1, 10] - Cross-attention weights over the 10 timesteps
        """
        # Image branch
        image_feat = self.image_projection(image)  # [B, 256]

        # Satellite temporal branch
        sat_out, _ = self.satellite_lstm(satellite)  # [B, 10, 256]
        sat_feat = self.satellite_projection(sat_out)  # [B, 10, 256]

        # Query = Image, Key/Value = Satellite
        query = image_feat.unsqueeze(1)  # [B, 1, 256]
        attended, attention = self.cross_attention(
            query, sat_feat, sat_feat
        )  # attended: [B, 1, 256], attention: [B, 1, 10]

        # Residual connection + LayerNorm
        attended = self.attention_norm(attended + query).squeeze(1)  # [B, 256]

        # Concatenation fusion
        fused = torch.cat([image_feat, attended], dim=1)  # [B, 512]
        fused = self.fusion(fused)  # [B, 128]

        # Final classification logits
        logits = self.classifier(fused)  # [B, 11]

        return logits, attention


class MultimodalModelLoader:
    """
    Manages loading, validating, and caching the trained TemporalCrossAttentionModel checkpoint.
    Guarantees strict weight verification, CPU device compatibility,
    and metadata extraction (normalization parameters, class ordering).
    """

    _instance: Optional["MultimodalModelLoader"] = None
    _model: Optional[TemporalCrossAttentionModel] = None
    _checkpoint_metadata: Dict[str, Any] = {}
    _load_status: str = "not_loaded"
    _last_error: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MultimodalModelLoader, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_status(cls) -> str:
        """
        Returns model residency status: 'loaded', 'not_loaded', or 'failed'.
        """
        if cls._model is not None:
            return "loaded"
        if cls._load_status == "failed":
            return "failed"
        return "not_loaded"

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._model is not None

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Returns cached checkpoint metadata. Loads checkpoint if not yet loaded.
        """
        if cls._model is None:
            cls.load_model()
        return cls._checkpoint_metadata

    @classmethod
    def get_model(cls) -> TemporalCrossAttentionModel:
        """
        Retrieves the cached Multimodal Cross-Attention model.
        Loads from disk if not already resident in memory.
        """
        if cls._model is None:
            return cls.load_model()
        return cls._model

    @classmethod
    def load_model(
        cls, checkpoint_path: Optional[Path] = None
    ) -> TemporalCrossAttentionModel:
        """
        Loads the trained multimodal weights onto CPU with strict verification.
        """
        target_path = checkpoint_path or config.MULTIMODAL_CHECKPOINT_PATH

        if checkpoint_path is None and cls._model is not None:
            return cls._model

        if not target_path.exists():
            cls._load_status = "failed"
            cls._last_error = f"Multimodal checkpoint not found at: {target_path}"
            logger.error("Multimodal checkpoint not found at: %s", target_path)
            raise FileNotFoundError(f"Multimodal checkpoint file does not exist: {target_path}")

        try:
            logger.info(
                "Loading TemporalCrossAttentionModel from %s onto %s...",
                target_path,
                config.DEVICE,
            )
            checkpoint = torch.load(
                target_path,
                map_location=torch.device(config.DEVICE),
                weights_only=False,
            )

            # Extract and verify architecture metadata
            arch_name = checkpoint.get("architecture", "")
            class_names = checkpoint.get("class_names", config.MULTIMODAL_CLASSES)
            num_classes = checkpoint.get("num_classes", len(class_names))
            sat_mean = checkpoint.get("satellite_mean")
            sat_std = checkpoint.get("satellite_std")

            if sat_mean is None or sat_std is None:
                raise ValueError("Checkpoint is missing mandatory satellite normalization parameters (satellite_mean, satellite_std).")

            cls._checkpoint_metadata = {
                "architecture": arch_name,
                "class_names": class_names,
                "num_classes": num_classes,
                "best_val_accuracy": float(checkpoint.get("best_val_accuracy", 0.0)),
                "best_val_f1": float(checkpoint.get("best_val_f1", checkpoint.get("best_val_macro_f1", 0.0))),
                "satellite_mean": np.array(sat_mean, dtype=np.float32),
                "satellite_std": np.array(sat_std, dtype=np.float32),
                "image_dim": checkpoint.get("image_dim", 1792),
                "num_heads": checkpoint.get("num_heads", 8),
                "checkpoint_path": str(target_path),
            }

            model = TemporalCrossAttentionModel(
                image_dim=cls._checkpoint_metadata["image_dim"],
                hidden_dim=128,
                attention_dim=256,
                num_heads=cls._checkpoint_metadata["num_heads"],
                num_classes=num_classes,
            )

            state_dict = checkpoint.get("model_state_dict", checkpoint)
            missing_keys, unexpected_keys = model.load_state_dict(state_dict, strict=True)
            if missing_keys or unexpected_keys:
                raise RuntimeError(
                    f"Multimodal checkpoint parameter mismatch: missing={missing_keys}, unexpected={unexpected_keys}"
                )

            model.to(config.DEVICE)
            model.eval()

            cls._model = model
            cls._load_status = "loaded"
            cls._last_error = None
            logger.info(
                "TemporalCrossAttentionModel loaded successfully (%d classes, best val acc: %.2f%%).",
                num_classes,
                cls._checkpoint_metadata["best_val_accuracy"] * 100,
            )
            return cls._model

        except Exception as e:
            cls._load_status = "failed"
            cls._last_error = str(e)
            logger.error("Failed to load Multimodal Cross-Attention model: %s", e, exc_info=True)
            raise
