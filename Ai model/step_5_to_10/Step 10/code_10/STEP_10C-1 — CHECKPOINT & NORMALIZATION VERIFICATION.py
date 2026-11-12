# ============================================================
# STEP 10C-1 — CHECKPOINT & NORMALIZATION VERIFICATION
# ============================================================

import torch
import numpy as np
from pathlib import Path

print("=" * 70)
print("STEP 10C-1 — CHECKPOINT VERIFICATION")
print("=" * 70)

BASE = Path("/content/drive/MyDrive/final year project")

CHECKPOINT_PATH = (
    BASE
    / "AI_model/step_5_to_9/Step 7/models_7/"
    "Step7L_Temporal_CrossAttention_m_1/"
    "step7L_controlled_best.pth"
)

BACKGROUND_PATH = (
    BASE
    / "AI_model/step_5_to_9/Step 8/SHAP_Results/"
    "shap_satellite_background.npy"
)

print("\nCheckpoint exists:", CHECKPOINT_PATH.is_file())
print("Background exists:", BACKGROUND_PATH.is_file())

if not CHECKPOINT_PATH.is_file():
    raise FileNotFoundError(
        f"Checkpoint not found: {CHECKPOINT_PATH}"
    )

if not BACKGROUND_PATH.is_file():
    raise FileNotFoundError(
        f"SHAP background not found: {BACKGROUND_PATH}"
    )

# Load checkpoint on CPU for inspection.
checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location="cpu",
    weights_only=False
)

print("\nCheckpoint type:", type(checkpoint).__name__)

if not isinstance(checkpoint, dict):
    raise TypeError("Unexpected checkpoint format.")

print("Checkpoint keys:", list(checkpoint.keys()))

# Show saved model configuration, if available.
for key in [
    "architecture",
    "num_classes",
    "class_names",
    "image_dim",
    "satellite_input_dim",
    "satellite_timesteps",
    "projection_dim",
    "num_heads",
    "satellite_mean",
    "satellite_std",
]:
    if key in checkpoint:
        print(f"\n{key}:")
        print(checkpoint[key])

# Load and inspect SHAP background.
background = np.load(
    BACKGROUND_PATH,
    allow_pickle=False
)

print("\nBackground shape:", background.shape)
print("Background dtype:", background.dtype)
print("Background finite:", bool(np.isfinite(background).all()))

if background.ndim != 3 or background.shape[1:] != (10, 3):
    raise ValueError(
        f"Unexpected background shape: {background.shape}"
    )

if not np.isfinite(background).all():
    raise ValueError("Background contains NaN or infinite values.")

print("\nSTEP 10C-1 COMPLETED")
print("Checkpoint and background files verified.")