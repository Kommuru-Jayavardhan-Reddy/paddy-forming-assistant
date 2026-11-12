
# ============================================================
# STEP 10B — SHAP BACKGROUND DATASET PREPARATION
# CORRECTED VERSION
# ============================================================

import numpy as np
import pandas as pd
from pathlib import Path

print("=" * 70)
print("STEP 10B — SHAP BACKGROUND DATASET PREPARATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. PROJECT PATHS — CORRECTED
# ------------------------------------------------------------

BASE = Path("/content/drive/MyDrive/final year project")

SATELLITE_PATH = (
    BASE
    / "AI_model/step_5_to_9/Step 5/models_5/"
    "bilstm_sequences.npy"
)

MAPPING_PATH = (
    BASE
    / "AI_model/step_5_to_9/Step 7/"
    "step7_verified_field_embedding_mapping.csv"
)

DATASET_PATH = (
    BASE
    / "AI_model/step_5_to_9/Step 7/"
    "text_and_csv_files_7/"
    "step7I_final_11class_multimodal_dataset.csv"
)

# ------------------------------------------------------------
# 2. VERIFY FILES
# ------------------------------------------------------------

print("\n[1/6] Checking required files...")

required_files = {
    "Satellite sequences": SATELLITE_PATH,
    "Field mapping": MAPPING_PATH,
    "Multimodal dataset": DATASET_PATH,
}

missing_files = []

for name, path in required_files.items():
    exists = path.is_file()

    print(f"\n{name}:")
    print("Path:", path)
    print("Exists:", exists)

    if not exists:
        missing_files.append(name)

if missing_files:
    raise FileNotFoundError(
        "Missing files: " + ", ".join(missing_files)
        + "\nPlease verify the paths before continuing."
    )

# ------------------------------------------------------------
# 3. LOAD DATA
# ------------------------------------------------------------

print("\n[2/6] Loading data...")

satellite_sequences = np.load(
    SATELLITE_PATH,
    allow_pickle=False
)

field_mapping = pd.read_csv(MAPPING_PATH)
dataset = pd.read_csv(DATASET_PATH)

print("Satellite shape:", satellite_sequences.shape)
print("Field mapping shape:", field_mapping.shape)
print("Dataset shape:", dataset.shape)

print("\nMapping columns:")
print(field_mapping.columns.tolist())

print("\nDataset columns:")
print(dataset.columns.tolist())

# ------------------------------------------------------------
# 4. VALIDATE SATELLITE SEQUENCES
# ------------------------------------------------------------

print("\n[3/6] Validating satellite data...")

if satellite_sequences.ndim != 3:
    raise ValueError(
        f"Expected 3D satellite data; got "
        f"{satellite_sequences.shape}"
    )

if satellite_sequences.shape[1:] != (10, 3):
    raise ValueError(
        f"Expected shape (N, 10, 3); got "
        f"{satellite_sequences.shape}"
    )

if len(satellite_sequences) == 0:
    raise ValueError("Satellite dataset is empty.")

if not np.issubdtype(
    satellite_sequences.dtype, np.number
):
    raise TypeError("Satellite data must contain numeric values.")

if not np.isfinite(satellite_sequences).all():
    raise ValueError(
        "Satellite data contains NaN or infinite values."
    )

print("Satellite validation: PASSED")
print("Number of sequences:", len(satellite_sequences))
print("Timesteps:", satellite_sequences.shape[1])
print("Features per timestep:", satellite_sequences.shape[2])

# ------------------------------------------------------------
# 5. VALIDATE FIELD MAPPING
# ------------------------------------------------------------

print("\n[4/6] Validating field mapping...")

required_mapping_columns = {
    "field_id",
    "sequence_index",
}

missing_mapping_columns = (
    required_mapping_columns - set(field_mapping.columns)
)

if missing_mapping_columns:
    raise ValueError(
        "Missing mapping columns: "
        + str(sorted(missing_mapping_columns))
    )

if field_mapping["field_id"].isna().any():
    raise ValueError("Field mapping contains missing field IDs.")

if field_mapping["sequence_index"].isna().any():
    raise ValueError("Field mapping contains missing sequence indices.")

sequence_indices = pd.to_numeric(
    field_mapping["sequence_index"],
    errors="raise"
)

if not np.all(
    sequence_indices.to_numpy()
    == np.floor(sequence_indices.to_numpy())
):
    raise ValueError("Sequence indices must be integers.")

sequence_indices = sequence_indices.astype(int)

if sequence_indices.duplicated().any():
    raise ValueError(
        "Duplicate sequence indices found in field mapping."
    )

if not sequence_indices.between(
    0, len(satellite_sequences) - 1
).all():
    raise ValueError(
        "Mapping contains sequence indices outside the "
        "satellite array range."
    )

print("Field mapping validation: PASSED")
print("Mapped fields:", len(field_mapping))

# ------------------------------------------------------------
# 6. PREPARE AND SAVE SHAP BACKGROUND
# ------------------------------------------------------------

print("\n[5/6] Preparing SHAP background samples...")

rng = np.random.default_rng(42)

n_background = min(20, len(satellite_sequences))

background_indices = np.sort(
    rng.choice(
        len(satellite_sequences),
        size=n_background,
        replace=False
    )
)

shap_background = satellite_sequences[
    background_indices
].astype(np.float32)

if not np.isfinite(shap_background).all():
    raise ValueError("SHAP background contains invalid values.")

print("Background shape:", shap_background.shape)
print("Selected indices:", background_indices.tolist())

# ------------------------------------------------------------
# 7. SAVE OUTPUTS
# ------------------------------------------------------------

print("\n[6/6] Saving SHAP background...")

OUTPUT_DIR = (
    BASE
    / "AI_model/step_5_to_9/Step 8/SHAP_Results"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

BACKGROUND_PATH = (
    OUTPUT_DIR / "shap_satellite_background.npy"
)

np.save(
    BACKGROUND_PATH,
    shap_background,
    allow_pickle=False
)

# Save selected indices for reproducibility.
INDEX_PATH = (
    OUTPUT_DIR / "shap_background_indices.npy"
)

np.save(
    INDEX_PATH,
    background_indices,
    allow_pickle=False
)

# Verify saved file.
saved_background = np.load(
    BACKGROUND_PATH,
    allow_pickle=False
)

if not np.array_equal(saved_background, shap_background):
    raise RuntimeError(
        "Saved background verification failed."
    )

print("\nBackground saved:", BACKGROUND_PATH)
print("Background indices saved:", INDEX_PATH)
print("Verified saved shape:", saved_background.shape)

print("\n" + "=" * 70)
print("STEP 10B COMPLETED SUCCESSFULLY")
print("=" * 70)

