# ============================================================================
# STEP_7.4 FIX — CORRECT FIELD → SATELLITE EMBEDDING INDEX
# ============================================================================

import os
import numpy as np
import pandas as pd

BASE_DIR = "/content/drive/MyDrive/final year project/Real_world_test"

STEP5_DIR = os.path.join(BASE_DIR, "Step 5")
STEP6_DIR = os.path.join(BASE_DIR, "Step 6")
STEP7_DIR = os.path.join(BASE_DIR, "Step 7")

IMAGE_MAPPING_FILE = os.path.join(
    STEP5_DIR,
    "step5C3_image_to_satellite_mapping_candidates.csv"
)

EMBEDDING_FILE = os.path.join(
    STEP6_DIR,
    "step6F_final_satellite_embeddings.npy"
)

OUTPUT_MAPPING = os.path.join(
    STEP7_DIR,
    "step7_FINAL_image_field_satellite_mapping.csv"
)

OUTPUT_EMBEDDINGS = os.path.join(
    STEP7_DIR,
    "step7_FINAL_satellite_embeddings.npy"
)

OUTPUT_INDEX = os.path.join(
    STEP7_DIR,
    "step7_FINAL_image_embedding_index.csv"
)

# ============================================================================
# LOAD
# ============================================================================

print("=" * 80)
print("STEP 7 — INDEX CORRECTION")
print("=" * 80)

df = pd.read_csv(IMAGE_MAPPING_FILE)

confirmed = df[
    df["decision"] == "CONFIRMED"
].copy()

embeddings = np.load(
    EMBEDDING_FILE
)

print(f"\nConfirmed images: {len(confirmed)}")
print(f"Step 6 embeddings: {embeddings.shape}")

# ============================================================================
# CORRECT MAPPING
# ============================================================================
# IMPORTANT:
# FIELD_01 → embedding[0]
# FIELD_02 → embedding[1]
# ...
# FIELD_58 → embedding[57]

field_to_embedding_index = {
    f"FIELD_{i:02d}": i - 1
    for i in range(1, 59)
}

confirmed["satellite_embedding_index"] = (
    confirmed["nearest_satellite_field"]
    .astype(str)
    .map(field_to_embedding_index)
)

# ============================================================================
# VERIFY NO MISSING INDEX
# ============================================================================

if confirmed["satellite_embedding_index"].isna().any():

    missing_fields = (
        confirmed[
            confirmed["satellite_embedding_index"].isna()
        ]["nearest_satellite_field"]
        .unique()
        .tolist()
    )

    raise ValueError(
        f"Missing embedding mapping for: {missing_fields}"
    )

confirmed["satellite_embedding_index"] = (
    confirmed["satellite_embedding_index"]
    .astype(int)
)

# ============================================================================
# ADD 256-D EMBEDDINGS
# ============================================================================

confirmed["satellite_embedding"] = (
    confirmed["satellite_embedding_index"]
    .apply(
        lambda idx: embeddings[idx].tolist()
    )
)

# ============================================================================
# CREATE FINAL EMBEDDING MATRIX
# ============================================================================

final_embeddings = np.vstack(
    confirmed["satellite_embedding_index"]
    .apply(
        lambda idx: embeddings[idx]
    )
    .values
)

# ============================================================================
# SAVE
# ============================================================================

confirmed.to_csv(
    OUTPUT_MAPPING,
    index=False
)

np.save(
    OUTPUT_EMBEDDINGS,
    final_embeddings
)

# Clean index file
index_cols = [
    "nearest_satellite_field",
    "satellite_embedding_index",
    "distance_km"
]

if "image_name" in confirmed.columns:
    index_cols.insert(0, "image_name")

index_df = confirmed[
    [
        c for c in index_cols
        if c in confirmed.columns
    ]
].copy()

index_df.to_csv(
    OUTPUT_INDEX,
    index=False
)

# ============================================================================
# VERIFICATION
# ============================================================================

print("\n" + "=" * 80)
print("CORRECTED STEP 7 VERIFICATION")
print("=" * 80)

print(
    f"\n[1] Confirmed images: "
    f"{len(confirmed)}"
)

print(
    f"[2] Unique GPS fields: "
    f"{confirmed['gps_field_id'].nunique()}"
)

print(
    f"[3] Unique satellite fields: "
    f"{confirmed['nearest_satellite_field'].nunique()}"
)

print(
    f"[4] Final embedding shape: "
    f"{final_embeddings.shape}"
)

print(
    f"[5] NaN values: "
    f"{np.isnan(final_embeddings).sum()}"
)

print(
    f"[6] Infinite values: "
    f"{np.isinf(final_embeddings).sum()}"
)

print(
    f"[7] Maximum GPS → satellite distance: "
    f"{confirmed['distance_km'].max():.6f} km"
)

print(
    f"[8] Minimum embedding index: "
    f"{confirmed['satellite_embedding_index'].min()}"
)

print(
    f"[9] Maximum embedding index: "
    f"{confirmed['satellite_embedding_index'].max()}"
)

# ============================================================================
# SHOW FIELD MAPPING
# ============================================================================

print("\n[10] CORRECT FIELD → EMBEDDING INDEX")

used_fields = sorted(
    confirmed["nearest_satellite_field"].unique(),
    key=lambda x: field_to_embedding_index[x]
)

for field in used_fields:

    idx = field_to_embedding_index[field]

    count = (
        confirmed[
            confirmed["nearest_satellite_field"] == field
        ].shape[0]
    )

    print(
        f"{field} → embedding[{idx}] → {count} images"
    )

# ============================================================================
# CONSISTENCY CHECK
# ============================================================================

print("\n[11] Embedding consistency check...")

consistency = True

for _, row in confirmed.iterrows():

    idx = int(
        row["satellite_embedding_index"]
    )

    stored = np.asarray(
        row["satellite_embedding"],
        dtype=np.float32
    )

    original = embeddings[idx]

    if not np.allclose(
        stored,
        original,
        atol=1e-6
    ):

        consistency = False
        break

print(
    "Embedding consistency:",
    "PASS" if consistency else "FAIL"
)

# ============================================================================
# FINAL
# ============================================================================

print("\n" + "=" * 80)
print("STEP 7.4 INDEX FIX COMPLETE")
print("=" * 80)

print("\nCorrect mapping:")
print("FIELD_01 → embedding[0]")
print("FIELD_02 → embedding[1]")
print("FIELD_03 → embedding[2]")
print("...")
print("FIELD_58 → embedding[57]")

print("\nFiles updated:")
print(OUTPUT_MAPPING)
print(OUTPUT_EMBEDDINGS)
print(OUTPUT_INDEX)

print("\nDO NOT START MULTIMODAL TRAINING YET.")
print("=" * 80)