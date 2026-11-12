# ================================================================
# STEP 10E — BALANCED VALIDATION SHAP ANALYSIS
# Paddy Farming Assistant
# ================================================================

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import shap
import matplotlib.pyplot as plt

from pathlib import Path
from tqdm.auto import tqdm

print("=" * 70)
print("STEP 10E — BALANCED VALIDATION SHAP ANALYSIS")
print("=" * 70)

# ------------------------------------------------
# 1. CHECK EXISTING MODEL AND SHAP BACKGROUND
# ------------------------------------------------

required_vars = [
    "model",
    "checkpoint",
    "background_normalized",
    "device"
]

missing_vars = [
    name for name in required_vars
    if name not in globals()
]

if missing_vars:
    raise RuntimeError(
        f"Missing variables: {missing_vars}. "
        "Run the previous model-loading and SHAP background cells first."
    )

model.eval()

# ------------------------------------------------
# 2. FILE PATHS
# ------------------------------------------------

BASE = Path(
    "/content/drive/MyDrive/final year project/AI_model/"
    "step_5_to_9/Step 7"
)

CSV_PATH = BASE / "text_and_csv_files_7" / (
    "step7I_final_11class_multimodal_dataset.csv"
)

EMBEDDING_PATH = BASE / "models_7" / (
    "step7_FINAL_image_embeddings_1792.npy"
)

SATELLITE_PATH = Path(
    "/content/drive/MyDrive/final year project/AI_model/"
    "step_5_to_9/Step 5/models_5/bilstm_sequences.npy"
)

MAPPING_PATH = BASE / "step7_verified_field_embedding_mapping.csv"

OUTPUT_DIR = Path(
    "/content/drive/MyDrive/final year project/AI_model/"
    "step_5_to_9/Step 8/SHAP_Results"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------
# 3. LOAD DATA
# ------------------------------------------------

df = pd.read_csv(CSV_PATH)
image_embeddings = np.load(EMBEDDING_PATH)
satellite_sequences = np.load(SATELLITE_PATH)
field_mapping = pd.read_csv(MAPPING_PATH)

print("\nDataset shape:", df.shape)
print("Image embeddings shape:", image_embeddings.shape)
print("Satellite sequences shape:", satellite_sequences.shape)

# ------------------------------------------------
# 4. VALIDATE DATA
# ------------------------------------------------

required_columns = [
    "image_embedding_index",
    "nearest_satellite_field",
    "label_11class",
    "split"
]

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns: {missing_columns}"
    )

mapping_required = ["field_id", "sequence_index"]

if not all(
    column in field_mapping.columns
    for column in mapping_required
):
    raise ValueError(
        "Field mapping CSV must contain field_id and sequence_index."
    )

field_mapping = field_mapping[
    mapping_required
].drop_duplicates("field_id")

field_to_sequence = dict(
    zip(
        field_mapping["field_id"].astype(str).str.strip(),
        field_mapping["sequence_index"].astype(int)
    )
)

# ------------------------------------------------
# 5. SELECT VALIDATION DATA
# ------------------------------------------------

val_df = df[
    df["split"].astype(str).str.strip().str.lower()
    == "validation"
].copy()

print("\nValidation samples available:", len(val_df))

if val_df.empty:
    raise ValueError("No validation samples found.")

# ------------------------------------------------
# 6. CREATE VALID SAMPLE RECORDS
# ------------------------------------------------

candidate_records = []

for row_index, row in val_df.iterrows():

    try:
        image_idx = int(row["image_embedding_index"])
        field_id = str(row["nearest_satellite_field"]).strip()
        label = int(row["label_11class"])

        if not 0 <= image_idx < len(image_embeddings):
            continue

        if not 0 <= label < 11:
            continue

        if field_id not in field_to_sequence:
            continue

        sequence_idx = field_to_sequence[field_id]

        if not 0 <= sequence_idx < len(satellite_sequences):
            continue

        candidate_records.append({
            "row_index": int(row_index),
            "image_idx": image_idx,
            "field_id": field_id,
            "sequence_idx": sequence_idx,
            "true_label": label
        })

    except (ValueError, TypeError, KeyError):
        continue

candidates_df = pd.DataFrame(candidate_records)

if candidates_df.empty:
    raise ValueError(
        "No valid validation samples found after mapping checks."
    )

print("Valid validation samples:", len(candidates_df))

# ------------------------------------------------
# 7. BALANCED CLASS SAMPLING
# ------------------------------------------------
# Select up to 2 samples per class.
# This avoids selecting only the first class from the CSV.

MAX_PER_CLASS = 2
RANDOM_SEED = 42

balanced_records = []

for class_id, group in candidates_df.groupby("true_label"):

    n_select = min(MAX_PER_CLASS, len(group))

    selected = group.sample(
        n=n_select,
        random_state=RANDOM_SEED
    )

    balanced_records.extend(
        selected.to_dict("records")
    )

if not balanced_records:
    raise ValueError("Balanced sampling returned no samples.")

# Stable order for reproducibility
balanced_records = sorted(
    balanced_records,
    key=lambda x: (x["true_label"], x["row_index"])
)

print("\nBalanced sample count:", len(balanced_records))

print("\nSelected samples per class:")
print(
    pd.Series(
        [r["true_label"] for r in balanced_records]
    ).value_counts().sort_index()
)

# ------------------------------------------------
# 8. CREATE SHAP WRAPPER
# ------------------------------------------------

class SatelliteClassWrapperBalanced(nn.Module):

    def __init__(self, base_model, image_embedding, target_class):
        super().__init__()

        self.base_model = base_model
        self.image_embedding = image_embedding
        self.target_class = int(target_class)

    def forward(self, satellite_input):

        batch_size = satellite_input.shape[0]

        image_input = self.image_embedding.expand(
            batch_size, -1
        )

        output = self.base_model(
            image_input,
            satellite_input
        )

        # Selected class logit: shape (batch, 1)
        return output[:, self.target_class].unsqueeze(1)


# ------------------------------------------------
# 9. SATELLITE NORMALIZATION
# ------------------------------------------------

sat_mean = torch.as_tensor(
    checkpoint["satellite_mean"],
    dtype=torch.float32,
    device=device
).reshape(1, 1, 3)

sat_std = torch.as_tensor(
    checkpoint["satellite_std"],
    dtype=torch.float32,
    device=device
).reshape(1, 1, 3)

sat_std = torch.clamp(sat_std, min=1e-8)

feature_names = ["NDVI", "NDRE", "GNDVI"]

# Ensure background is on the same device as the model.
background = background_normalized.to(device)

all_shap_values = []
summary_rows = []

# ------------------------------------------------
# 10. CALCULATE SHAP
# ------------------------------------------------

for sample_no, record in enumerate(
    tqdm(balanced_records, desc="Balanced SHAP")
):

    image_idx = record["image_idx"]
    sequence_idx = record["sequence_idx"]
    target_class = record["true_label"]

    image_tensor = torch.as_tensor(
        image_embeddings[image_idx],
        dtype=torch.float32,
        device=device
    ).unsqueeze(0)

    satellite_raw = satellite_sequences[sequence_idx]

    satellite_tensor = torch.as_tensor(
        satellite_raw,
        dtype=torch.float32,
        device=device
    ).unsqueeze(0)

    satellite_normalized = (
        satellite_tensor - sat_mean
    ) / sat_std

    wrapper = SatelliteClassWrapperBalanced(
        base_model=model,
        image_embedding=image_tensor,
        target_class=target_class
    ).to(device)

    wrapper.eval()

    explainer = shap.GradientExplainer(
        wrapper,
        background
    )

    shap_result = explainer.shap_values(
        satellite_normalized,
        nsamples=100
    )

    shap_array = np.asarray(shap_result).squeeze()

    if shap_array.shape != (10, 3):
        raise ValueError(
            f"Sample {sample_no}: unexpected SHAP shape "
            f"{shap_array.shape}; expected (10, 3)."
        )

    if not np.isfinite(shap_array).all():
        raise ValueError(
            f"Non-finite SHAP values in sample {sample_no}."
        )

    all_shap_values.append(shap_array)

    importance = np.mean(
        np.abs(shap_array),
        axis=0
    )

    summary_rows.append({
        "sample_no": sample_no,
        "dataset_row_index": record["row_index"],
        "image_embedding_index": image_idx,
        "field_id": record["field_id"],
        "satellite_sequence_index": sequence_idx,
        "true_label": target_class,
        "NDVI_mean_abs_SHAP": importance[0],
        "NDRE_mean_abs_SHAP": importance[1],
        "GNDVI_mean_abs_SHAP": importance[2]
    })

# ------------------------------------------------
# 11. SAVE RESULTS
# ------------------------------------------------

summary_df = pd.DataFrame(summary_rows)

summary_csv = OUTPUT_DIR / (
    "step10E_balanced_validation_shap_summary.csv"
)

summary_df.to_csv(
    summary_csv,
    index=False
)

stacked_shap = np.stack(
    all_shap_values,
    axis=0
)

shap_npy = OUTPUT_DIR / (
    "step10E_balanced_validation_shap_values.npy"
)

np.save(shap_npy, stacked_shap)

# ------------------------------------------------
# 12. AGGREGATED FEATURE IMPORTANCE
# ------------------------------------------------

global_importance = np.mean(
    np.abs(stacked_shap),
    axis=(0, 1)
)

importance_df = pd.DataFrame({
    "Satellite_Feature": feature_names,
    "Mean_Absolute_SHAP": global_importance
}).sort_values(
    "Mean_Absolute_SHAP",
    ascending=False
)

importance_csv = OUTPUT_DIR / (
    "step10E_balanced_feature_importance.csv"
)

importance_df.to_csv(
    importance_csv,
    index=False
)

# ------------------------------------------------
# 13. PLOT FEATURE IMPORTANCE
# ------------------------------------------------

plt.figure(figsize=(8, 5))

plt.bar(
    importance_df["Satellite_Feature"],
    importance_df["Mean_Absolute_SHAP"]
)

plt.ylabel("Mean Absolute SHAP Value")
plt.xlabel("Satellite Feature")

plt.title(
    f"Satellite Feature Importance "
    f"({len(balanced_records)} Balanced Validation Samples)"
)

plt.tight_layout()

plot_path = OUTPUT_DIR / (
    "step10E_balanced_feature_importance.png"
)

plt.savefig(
    plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

# ------------------------------------------------
# 14. FINAL VERIFICATION
# ------------------------------------------------

print("\n" + "=" * 70)
print("STEP 10E — BALANCED SHAP COMPLETED")
print("=" * 70)

print("Samples analysed:", len(all_shap_values))
print("SHAP array shape:", stacked_shap.shape)

print("\nFeature importance:")
print(importance_df.to_string(index=False))

print("\nSaved files:")
print("Summary CSV:", summary_csv)
print("SHAP values:", shap_npy)
print("Importance CSV:", importance_csv)
print("Feature importance plot:", plot_path)

print("\nSample summary:")
display(summary_df)