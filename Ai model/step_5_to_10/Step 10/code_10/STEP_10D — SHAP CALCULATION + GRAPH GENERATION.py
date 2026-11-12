
# ============================================================
# STEP 10D — SHAP CALCULATION + GRAPH GENERATION
# ============================================================

import shap
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from pathlib import Path

print("=" * 70)
print("STEP 10D — SHAP CALCULATION AND VISUALIZATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. VERIFY VARIABLES
# ------------------------------------------------------------

required_variables = [
    "model",
    "fixed_image",
    "target_class",
    "background_normalized",
    "sample_satellite_normalized",
    "device",
    "checkpoint",
]

for name in required_variables:
    if name not in globals():
        raise RuntimeError(
            f"Variable '{name}' not found. "
            "Run STEP 10C-2 successfully first."
        )

BASE = Path("/content/drive/MyDrive/final year project")

OUTPUT_DIR = (
    BASE / "AI_model/step_5_to_9/Step 8/SHAP_Results"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 2. CREATE CORRECTED SHAP WRAPPER
# ------------------------------------------------------------

class SatelliteClassWrapperFixed(nn.Module):

    def __init__(self, base_model, image_embedding, target_class):
        super().__init__()

        self.base_model = base_model

        self.register_buffer(
            "fixed_image",
            image_embedding.detach().clone()
        )

        self.target_class = int(target_class)

    def forward(self, satellite_normalized):

        batch_size = satellite_normalized.shape[0]

        image_batch = self.fixed_image.expand(
            batch_size, -1
        )

        logits = self.base_model(
            image_batch,
            satellite_normalized
        )

        if isinstance(logits, (tuple, list)):
            logits = logits[0]

        # Keep output in (batch_size, 1) format.
        return logits[
            :, self.target_class:self.target_class + 1
        ]


shap_model_fixed = SatelliteClassWrapperFixed(
    model,
    fixed_image,
    target_class
).to(device)

shap_model_fixed.eval()

# ------------------------------------------------------------
# 3. VERIFY OUTPUT SHAPE
# ------------------------------------------------------------

print("\n[1/5] Checking wrapper output...")

with torch.no_grad():
    test_output = shap_model_fixed(
        background_normalized[:2]
    )

print("Output shape:", tuple(test_output.shape))

if test_output.shape != (2, 1):
    raise ValueError(
        f"Expected (2, 1), got {tuple(test_output.shape)}"
    )

if not torch.isfinite(test_output).all():
    raise ValueError("Wrapper output contains invalid values.")

# ------------------------------------------------------------
# 4. CALCULATE SHAP VALUES
# ------------------------------------------------------------

print("\n[2/5] Creating GradientExplainer...")

explainer = shap.GradientExplainer(
    shap_model_fixed,
    background_normalized
)

print("GradientExplainer ready.")

print("\nCalculating SHAP values...")

shap_result = explainer.shap_values(
    sample_satellite_normalized,
    nsamples=100
)

shap_array = np.asarray(shap_result)

# SHAP 0.52.0 may return an additional output dimension.
shap_array = np.squeeze(shap_array)

if shap_array.shape != (10, 3):
    raise ValueError(
        f"Expected SHAP shape (10, 3), got {shap_array.shape}"
    )

if not np.isfinite(shap_array).all():
    raise ValueError("SHAP values contain NaN or infinity.")

print("SHAP shape:", shap_array.shape)
print("SHAP values are finite.")

# ------------------------------------------------------------
# 5. SAVE SHAP VALUES AND CSV
# ------------------------------------------------------------

print("\n[3/5] Saving SHAP results...")

np.save(
    OUTPUT_DIR / "shap_values_sample_0.npy",
    shap_array,
    allow_pickle=False
)

feature_names = ["NDVI", "NDRE", "GNDVI"]

normalized_values = (
    sample_satellite_normalized[0]
    .detach()
    .cpu()
    .numpy()
)

rows = []

for t in range(10):
    for j, feature in enumerate(feature_names):

        value = float(shap_array[t, j])

        rows.append({
            "time_step": t + 1,
            "feature": feature,
            "normalized_satellite_value": float(
                normalized_values[t, j]
            ),
            "shap_value": value,
            "absolute_shap_value": abs(value),
        })

shap_df = pd.DataFrame(rows)

csv_path = OUTPUT_DIR / "shap_values_sample_0.csv"
shap_df.to_csv(csv_path, index=False)

print("Saved:", OUTPUT_DIR / "shap_values_sample_0.npy")
print("Saved:", csv_path)

# ------------------------------------------------------------
# 6. GRAPH 1 — FEATURE IMPORTANCE
# ------------------------------------------------------------

print("\n[4/5] Creating feature importance graph...")

importance = np.abs(shap_array).mean(axis=0)

plt.figure(figsize=(8, 5))

plt.bar(feature_names, importance)

plt.xlabel("Satellite Feature")
plt.ylabel("Mean Absolute SHAP Value")
plt.title("Satellite Feature Importance — Sample 0")
plt.tight_layout()

importance_path = (
    OUTPUT_DIR / "shap_feature_importance_sample_0.png"
)

plt.savefig(
    importance_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved:", importance_path)

# ------------------------------------------------------------
# 7. GRAPH 2 — TIME-STEP HEATMAP
# ------------------------------------------------------------

print("\n[5/5] Creating time-step heatmap...")

plt.figure(figsize=(10, 5))

plt.imshow(
    shap_array.T,
    aspect="auto",
    interpolation="nearest"
)

plt.xticks(
    ticks=np.arange(10),
    labels=np.arange(1, 11)
)

plt.yticks(
    ticks=np.arange(3),
    labels=feature_names
)

plt.xlabel("Satellite Time Step")
plt.ylabel("Satellite Feature")
plt.title("SHAP Values Across Satellite Time Steps — Sample 0")

plt.colorbar(label="SHAP Value")

plt.tight_layout()

heatmap_path = (
    OUTPUT_DIR / "shap_satellite_heatmap_sample_0.png"
)

plt.savefig(
    heatmap_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved:", heatmap_path)

# ------------------------------------------------------------
# 8. FINAL SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 10D COMPLETED SUCCESSFULLY")
print("=" * 70)

print("\nOutput folder:")
print(OUTPUT_DIR)

print("\nFiles generated:")
for filename in [
    "shap_values_sample_0.npy",
    "shap_values_sample_0.csv",
    "shap_feature_importance_sample_0.png",
    "shap_satellite_heatmap_sample_0.png",
]:
    path = OUTPUT_DIR / filename
    print(f"{filename}: {'EXISTS' if path.exists() else 'MISSING'}")

print("\nMean absolute SHAP values:")
for feature, value in zip(feature_names, importance):
    print(f"{feature}: {value:.6f}")

