# =============================================================================
# STEP 7G — FINAL MULTIMODAL DATASET INTEGRITY CHECK
# =============================================================================

import os
import numpy as np
import pandas as pd

print("=" * 80)
print("STEP 7G — FINAL MULTIMODAL DATASET INTEGRITY CHECK")
print("=" * 80)


# =============================================================================
# 1. PATHS
# =============================================================================

FINAL_CSV = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7F_final_multimodal_dataset_640.csv"
)

IMAGE_EMBEDDINGS = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7_FINAL_image_embeddings_1792.npy"
)

SATELLITE_EMBEDDINGS = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7E_paired_satellite_embeddings_640x256.npy"
)

OUTPUT_REPORT = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7G_final_integrity_report.txt"
)


# =============================================================================
# 2. CHECK FILES
# =============================================================================

print("\n[1] CHECKING INPUT FILES")
print("-" * 80)

for path in [
    FINAL_CSV,
    IMAGE_EMBEDDINGS,
    SATELLITE_EMBEDDINGS
]:

    print(path)

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"\n❌ File not found:\n{path}"
        )

    print("✓ Exists")


# =============================================================================
# 3. LOAD DATA
# =============================================================================

print("\n[2] LOADING FINAL DATASET")
print("-" * 80)

df = pd.read_csv(FINAL_CSV)

image_embeddings = np.load(
    IMAGE_EMBEDDINGS
)

satellite_embeddings = np.load(
    SATELLITE_EMBEDDINGS
)

print("Dataset shape:", df.shape)
print("Image embeddings:", image_embeddings.shape)
print("Satellite embeddings:", satellite_embeddings.shape)


# =============================================================================
# 4. RECORD COUNT
# =============================================================================

print("\n[3] RECORD COUNT CHECK")
print("-" * 80)

if len(df) != 640:

    raise RuntimeError(
        f"Expected 640 records, found {len(df)}"
    )

print("✓ Dataset records = 640")


# =============================================================================
# 5. EMBEDDING SHAPES
# =============================================================================

print("\n[4] EMBEDDING SHAPE CHECK")
print("-" * 80)

if image_embeddings.shape != (640, 1792):

    raise RuntimeError(
        f"Wrong image embedding shape: "
        f"{image_embeddings.shape}"
    )

if satellite_embeddings.shape != (640, 256):

    raise RuntimeError(
        f"Wrong satellite embedding shape: "
        f"{satellite_embeddings.shape}"
    )

print("✓ Image embeddings = (640, 1792)")
print("✓ Satellite embeddings = (640, 256)")


# =============================================================================
# 6. IMAGE INDEX ALIGNMENT
# =============================================================================

print("\n[5] IMAGE INDEX ALIGNMENT")
print("-" * 80)

expected_indices = np.arange(640)

actual_indices = (
    df["image_embedding_index"]
    .to_numpy()
)

if not np.array_equal(
    actual_indices,
    expected_indices
):

    raise RuntimeError(
        "Image embedding index is not exactly 0–639."
    )

print("✓ Image embedding indices = 0–639")


# =============================================================================
# 7. PAIRED SATELLITE INDEX ALIGNMENT
# =============================================================================

print("\n[6] SATELLITE PAIR INDEX ALIGNMENT")
print("-" * 80)

expected_pair_indices = np.arange(640)

actual_pair_indices = (
    df["paired_satellite_embedding_index"]
    .to_numpy()
)

if not np.array_equal(
    actual_pair_indices,
    expected_pair_indices
):

    raise RuntimeError(
        "Paired satellite indices are not exactly 0–639."
    )

print("✓ Paired satellite indices = 0–639")


# =============================================================================
# 8. IMAGE NAME DUPLICATES
# =============================================================================

print("\n[7] IMAGE DUPLICATE CHECK")
print("-" * 80)

duplicate_images = (
    df["image_name"]
    .duplicated()
    .sum()
)

print(
    "Duplicate image names:",
    duplicate_images
)

if duplicate_images != 0:

    raise RuntimeError(
        "Duplicate image names detected."
    )

print("✓ No duplicate image names")


# =============================================================================
# 9. IMAGE PATH VALIDATION
# =============================================================================

print("\n[8] IMAGE FILE VALIDATION")
print("-" * 80)

missing_images = []

for path in df["image_path"]:

    if not isinstance(path, str):
        missing_images.append(path)

    elif not os.path.isfile(path):
        missing_images.append(path)

print(
    "Missing image files:",
    len(missing_images)
)

if len(missing_images) > 0:

    print("\nMissing paths:")

    for path in missing_images[:20]:
        print(path)

    raise RuntimeError(
        "One or more final dataset images are missing."
    )

print("✓ All 640 image files exist")


# =============================================================================
# 10. DISEASE LABEL VALIDATION
# =============================================================================

print("\n[9] DISEASE LABEL VALIDATION")
print("-" * 80)

EXPECTED_CLASSES = [
    "bacterial_leaf_blight",
    "bacterial_leaf_streak",
    "bacterial_panicle_blight",
    "blast",
    "brown_spot",
    "dead_heart",
    "downy_mildew",
    "hispa",
    "leaf_scald",
    "leaf_smut",
    "normal",
    "sheath_blight",
    "tungro"
]

if df["disease_label"].isna().any():

    raise RuntimeError(
        "Missing disease labels detected."
    )

unknown_labels = set(
    df["disease_label"].unique()
) - set(EXPECTED_CLASSES)

if unknown_labels:

    raise RuntimeError(
        f"Unknown disease labels: {unknown_labels}"
    )

print("✓ All disease labels valid")


# =============================================================================
# 11. CLASS INDEX VALIDATION
# =============================================================================

print("\n[10] CLASS INDEX VALIDATION")
print("-" * 80)

class_mapping = {
    cls: idx
    for idx, cls in enumerate(
        EXPECTED_CLASSES
    )
}

expected_class_indices = (
    df["disease_label"]
    .map(class_mapping)
    .to_numpy()
)

actual_class_indices = (
    df["disease_class_index"]
    .to_numpy()
)

if not np.array_equal(
    expected_class_indices,
    actual_class_indices
):

    raise RuntimeError(
        "Disease class indices do not match labels."
    )

print("✓ Disease label ↔ class index mapping correct")


# =============================================================================
# 12. SATELLITE FIELD VALIDATION
# =============================================================================

print("\n[11] SATELLITE FIELD VALIDATION")
print("-" * 80)

if df["nearest_satellite_field"].isna().any():

    raise RuntimeError(
        "Missing satellite field detected."
    )

unique_fields = (
    df["nearest_satellite_field"]
    .nunique()
)

print(
    "Unique satellite fields:",
    unique_fields
)

print("✓ All records have satellite fields")


# =============================================================================
# 13. SATELLITE INDEX VALIDATION
# =============================================================================

print("\n[12] SATELLITE INDEX VALIDATION")
print("-" * 80)

sat_indices = (
    df["satellite_embedding_index"]
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
        "Satellite embedding index outside 0–57."
    )

print(
    "Minimum satellite index:",
    sat_indices.min()
)

print(
    "Maximum satellite index:",
    sat_indices.max()
)

print("✓ Satellite embedding indices valid")


# =============================================================================
# 14. EMBEDDING NUMERICAL VALIDATION
# =============================================================================

print("\n[13] EMBEDDING NUMERICAL VALIDATION")
print("-" * 80)

image_nan = int(
    np.isnan(image_embeddings).sum()
)

image_inf = int(
    np.isinf(image_embeddings).sum()
)

sat_nan = int(
    np.isnan(satellite_embeddings).sum()
)

sat_inf = int(
    np.isinf(satellite_embeddings).sum()
)

print("Image NaN:", image_nan)
print("Image Inf:", image_inf)
print("Satellite NaN:", sat_nan)
print("Satellite Inf:", sat_inf)

if any([
    image_nan != 0,
    image_inf != 0,
    sat_nan != 0,
    sat_inf != 0
]):

    raise RuntimeError(
        "NaN or Inf detected."
    )

print("✓ All embeddings numerically valid")


# =============================================================================
# 15. IMAGE ↔ SATELLITE INDEX CONSISTENCY
# =============================================================================

print("\n[14] IMAGE ↔ SATELLITE INDEX CONSISTENCY")
print("-" * 80)

if len(df) != len(image_embeddings):

    raise RuntimeError(
        "Dataset rows and image embeddings are misaligned."
    )

if len(df) != len(satellite_embeddings):

    raise RuntimeError(
        "Dataset rows and satellite embeddings are misaligned."
    )

print("✓ 640 dataset rows")
print("✓ 640 image embeddings")
print("✓ 640 paired satellite embeddings")


# =============================================================================
# 16. DISTANCE VALIDATION
# =============================================================================

print("\n[15] GPS → SATELLITE DISTANCE VALIDATION")
print("-" * 80)

if "distance_km" in df.columns:

    distances = pd.to_numeric(
        df["distance_km"],
        errors="coerce"
    )

    print(
        "Missing distances:",
        distances.isna().sum()
    )

    print(
        "Maximum distance:",
        distances.max(),
        "km"
    )

    print(
        "Mean distance:",
        distances.mean(),
        "km"
    )

    if distances.isna().any():

        raise RuntimeError(
            "Missing GPS-to-satellite distances."
        )

    if (distances < 0).any():

        raise RuntimeError(
            "Negative distance detected."
        )

    print("✓ GPS-to-satellite distances valid")


# =============================================================================
# 17. DISEASE DISTRIBUTION
# =============================================================================

print("\n[16] FINAL DISEASE DISTRIBUTION")
print("-" * 80)

class_counts = (
    df["disease_label"]
    .value_counts()
    .reindex(
        EXPECTED_CLASSES,
        fill_value=0
    )
)

print(
    class_counts.to_string()
)

print(
    "\nTotal:",
    class_counts.sum()
)

zero_classes = (
    class_counts[
        class_counts == 0
    ]
    .index
    .tolist()
)

print(
    "\nZero-sample classes:",
    zero_classes
)


# =============================================================================
# 18. SATELLITE FIELD DISTRIBUTION
# =============================================================================

print("\n[17] FINAL SATELLITE FIELD DISTRIBUTION")
print("-" * 80)

field_counts = (
    df["nearest_satellite_field"]
    .value_counts()
    .sort_index()
)

print(field_counts.to_string())

print(
    "\nUnique satellite fields:",
    len(field_counts)
)


# =============================================================================
# 19. FINAL CHECK SUMMARY
# =============================================================================

print("\n[18] FINAL CHECK SUMMARY")
print("-" * 80)

checks = {

    "640 dataset records":
        len(df) == 640,

    "Image shape":
        image_embeddings.shape == (640, 1792),

    "Satellite shape":
        satellite_embeddings.shape == (640, 256),

    "Image indices":
        np.array_equal(
            actual_indices,
            np.arange(640)
        ),

    "Satellite pair indices":
        np.array_equal(
            actual_pair_indices,
            np.arange(640)
        ),

    "No duplicate images":
        duplicate_images == 0,

    "All image files exist":
        len(missing_images) == 0,

    "Disease labels valid":
        df["disease_label"].notna().all(),

    "Class indices valid":
        np.array_equal(
            expected_class_indices,
            actual_class_indices
        ),

    "Satellite fields valid":
        df["nearest_satellite_field"].notna().all(),

    "Satellite indices valid":
        (
            sat_indices.min() >= 0
            and sat_indices.max() < 58
        ),

    "Image NaN = 0":
        image_nan == 0,

    "Image Inf = 0":
        image_inf == 0,

    "Satellite NaN = 0":
        sat_nan == 0,

    "Satellite Inf = 0":
        sat_inf == 0
}


for name, result in checks.items():

    print(
        f"{name:30s}: "
        f"{'PASS' if result else 'FAIL'}"
    )


if not all(checks.values()):

    raise RuntimeError(
        "❌ One or more final integrity checks failed."
    )


# =============================================================================
# 20. SAVE REPORT
# =============================================================================

report = f"""
STEP 7G — FINAL MULTIMODAL DATASET INTEGRITY REPORT
====================================================

Dataset records:
640

Image embeddings:
(640, 1792)

Satellite embeddings:
(640, 256)

Duplicate image names:
{duplicate_images}

Missing image files:
{len(missing_images)}

Unique satellite fields:
{unique_fields}

Minimum satellite embedding index:
{sat_indices.min()}

Maximum satellite embedding index:
{sat_indices.max()}

Image NaN:
{image_nan}

Image Inf:
{image_inf}

Satellite NaN:
{sat_nan}

Satellite Inf:
{sat_inf}


DISEASE DISTRIBUTION
--------------------

{class_counts.to_string()}


ZERO-SAMPLE CLASSES
-------------------

{zero_classes}


FINAL STATUS
------------

ALL INTEGRITY CHECKS PASSED.
"""


with open(
    OUTPUT_REPORT,
    "w"
) as f:

    f.write(report)


print("\n✓ Report saved:")
print(OUTPUT_REPORT)


# =============================================================================
# FINAL
# =============================================================================

print("\n")
print("=" * 80)
print("STEP 7G — COMPLETE")
print("=" * 80)

print("""
✓ 640 image records
✓ 640 image embeddings (1792-D)
✓ 640 satellite embeddings (256-D)
✓ No duplicate images
✓ All image files exist
✓ Disease labels valid
✓ Disease class indices valid
✓ Satellite fields valid
✓ Satellite indices valid
✓ No NaN
✓ No Inf
✓ Image ↔ satellite alignment valid

IMPORTANT:
leaf_smut = 0
normal    = 0

These two classes are present in the original 13-class
model definition but have zero samples in this 640-image
real-world multimodal dataset.

Cross-Attention training has NOT been started.
""")

print("=" * 80)