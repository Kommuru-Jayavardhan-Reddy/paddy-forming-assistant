# =============================================================================
# STEP 7E — FINAL IMAGE + DISEASE + SATELLITE PAIR VERIFICATION
# =============================================================================

import os
import numpy as np
import pandas as pd

print("=" * 80)
print("STEP 7E — FINAL MULTIMODAL PAIR VERIFICATION")
print("=" * 80)


# =============================================================================
# 1. PATHS
# =============================================================================

IMAGE_INDEX = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7_FINAL_image_embedding_index.csv"
)

IMAGE_EMBEDDINGS = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7_FINAL_image_embeddings_1792.npy"
)

SATELLITE_EMBEDDINGS = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 6/"
    "step6F_final_satellite_embeddings.npy"
)

FIELD_CSV = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 5/"
    "clean_field_candidates_renamed.csv"
)

TIMESERIES_CSV = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 5/"
    "sentinel2_timeseries.csv"
)


# =============================================================================
# 2. CHECK FILES
# =============================================================================

print("\n[1] CHECKING FILES")
print("-" * 80)

paths = [
    IMAGE_INDEX,
    IMAGE_EMBEDDINGS,
    SATELLITE_EMBEDDINGS,
    FIELD_CSV,
    TIMESERIES_CSV
]

for path in paths:

    print(path)

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"\n❌ File not found:\n{path}"
        )

    print("✓ Exists")


# =============================================================================
# 3. LOAD IMAGE EMBEDDINGS
# =============================================================================

print("\n[2] LOADING IMAGE EMBEDDINGS")
print("-" * 80)

image_embeddings = np.load(
    IMAGE_EMBEDDINGS
)

print(
    "Image embedding shape:",
    image_embeddings.shape
)

if image_embeddings.shape != (640, 1792):

    raise RuntimeError(
        f"Expected (640,1792), "
        f"got {image_embeddings.shape}"
    )

print("✓ Image embeddings verified")


# =============================================================================
# 4. LOAD IMAGE INDEX
# =============================================================================

print("\n[3] LOADING IMAGE INDEX")
print("-" * 80)

image_df = pd.read_csv(
    IMAGE_INDEX
)

print(
    "Image index records:",
    len(image_df)
)

print("\nColumns:")
print(image_df.columns.tolist())


# =============================================================================
# 5. BASIC IMAGE INDEX CHECK
# =============================================================================

print("\n[4] IMAGE INDEX VALIDATION")
print("-" * 80)

if len(image_df) != 640:

    raise RuntimeError(
        f"Expected 640 records, "
        f"got {len(image_df)}"
    )

expected_indices = np.arange(640)

actual_indices = (
    image_df["image_embedding_index"]
    .to_numpy()
)

if not np.array_equal(
    actual_indices,
    expected_indices
):

    raise RuntimeError(
        "Image embedding indices are not sequential."
    )

print("✓ 640 image records")
print("✓ Embedding indices 0–639")
print("✓ Index order valid")


# =============================================================================
# 6. DISEASE LABEL CHECK
# =============================================================================

print("\n[5] DISEASE LABEL VERIFICATION")
print("-" * 80)

possible_label_columns = [
    "disease_label",
    "label",
    "class",
    "disease"
]

label_column = None

for col in possible_label_columns:

    if col in image_df.columns:

        label_column = col
        break

if label_column is None:

    print(
        "⚠ Disease label column was not found "
        "in the image embedding index."
    )

else:

    print(
        "Disease label column:",
        label_column
    )

    print(
        "Missing labels:",
        image_df[label_column].isna().sum()
    )

    print("\nDisease distribution:")

    print(
        image_df[label_column]
        .value_counts()
        .sort_index()
    )


# =============================================================================
# 7. LOAD SATELLITE EMBEDDINGS
# =============================================================================

print("\n[6] LOADING SATELLITE EMBEDDINGS")
print("-" * 80)

satellite_embeddings = np.load(
    SATELLITE_EMBEDDINGS
)

print(
    "Satellite embedding shape:",
    satellite_embeddings.shape
)

if satellite_embeddings.shape != (58, 256):

    raise RuntimeError(
        f"Expected (58,256), "
        f"got {satellite_embeddings.shape}"
    )

print("✓ Satellite embeddings verified")


# =============================================================================
# 8. VERIFY SATELLITE EMBEDDING INDICES
# =============================================================================

print("\n[7] SATELLITE INDEX VALIDATION")
print("-" * 80)

if "satellite_embedding_index" not in image_df.columns:

    raise RuntimeError(
        "satellite_embedding_index column missing."
    )

sat_indices = (
    image_df["satellite_embedding_index"]
    .to_numpy()
)

if np.isnan(sat_indices).any():

    raise RuntimeError(
        "Missing satellite embedding indices."
    )

sat_indices = sat_indices.astype(int)

if sat_indices.min() < 0:

    raise RuntimeError(
        "Negative satellite embedding index."
    )

if sat_indices.max() >= 58:

    raise RuntimeError(
        "Satellite embedding index >= 58."
    )

print(
    "Minimum index:",
    sat_indices.min()
)

print(
    "Maximum index:",
    sat_indices.max()
)

print("✓ All satellite indices valid")


# =============================================================================
# 9. BUILD MULTIMODAL PAIRS
# =============================================================================

print("\n[8] BUILDING MULTIMODAL PAIRS")
print("-" * 80)

paired_satellite_embeddings = (
    satellite_embeddings[
        sat_indices
    ]
)

print(
    "Paired satellite shape:",
    paired_satellite_embeddings.shape
)

if paired_satellite_embeddings.shape != (
    640,
    256
):

    raise RuntimeError(
        "Incorrect paired satellite shape."
    )

print("✓ 640 image ↔ satellite pairs created")


# =============================================================================
# 10. NUMERICAL VALIDATION
# =============================================================================

print("\n[9] NUMERICAL VALIDATION")
print("-" * 80)

checks = {
    "Image NaN":
        np.isnan(image_embeddings).sum(),

    "Image Inf":
        np.isinf(image_embeddings).sum(),

    "Satellite NaN":
        np.isnan(paired_satellite_embeddings).sum(),

    "Satellite Inf":
        np.isinf(paired_satellite_embeddings).sum()
}

for name, value in checks.items():

    print(
        f"{name}: {value}"
    )

if any(value != 0 for value in checks.values()):

    raise RuntimeError(
        "NaN or Inf detected."
    )

print("✓ All embeddings numerically valid")


# =============================================================================
# 11. FIELD DISTRIBUTION
# =============================================================================

print("\n[10] SATELLITE FIELD DISTRIBUTION")
print("-" * 80)

field_column_candidates = [
    "nearest_satellite_field",
    "satellite_field",
    "field_id"
]

field_column = None

for col in field_column_candidates:

    if col in image_df.columns:

        field_column = col
        break

if field_column is None:

    raise RuntimeError(
        "Satellite field column not found."
    )

print(
    "Field column:",
    field_column
)

field_counts = (
    image_df[field_column]
    .value_counts()
    .sort_index()
)

print(
    "\nUnique satellite fields:",
    field_counts.shape[0]
)

print("\nField distribution:")

print(field_counts.to_string())


# =============================================================================
# 12. SAVE PAIRED SATELLITE EMBEDDINGS
# =============================================================================

OUTPUT_PAIRED = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7E_paired_satellite_embeddings_640x256.npy"
)

np.save(
    OUTPUT_PAIRED,
    paired_satellite_embeddings.astype(
        np.float32
    )
)

print("\n✓ Saved paired satellite embeddings:")
print(OUTPUT_PAIRED)


# =============================================================================
# 13. FINAL STATUS
# =============================================================================

print("\n" + "=" * 80)
print("STEP 7E VERIFICATION RESULT")
print("=" * 80)

print("""
✓ Image embeddings        : (640, 1792)
✓ Satellite embeddings    : (58, 256)
✓ Paired satellite        : (640, 256)
✓ Satellite indices       : VALID
✓ NaN                     : 0
✓ Inf                     : 0
""")

print("=" * 80)