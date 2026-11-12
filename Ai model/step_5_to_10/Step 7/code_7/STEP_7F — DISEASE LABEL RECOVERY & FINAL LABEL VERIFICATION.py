# =============================================================================
# STEP_7F — DISEASE LABEL RECOVERY & FINAL LABEL VERIFICATION
# =============================================================================

import os
import numpy as np
import pandas as pd

print("=" * 80)
print("STEP 7F — DISEASE LABEL RECOVERY & VERIFICATION")
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
    "Real_world_test/Step 7/"
    "step7E_paired_satellite_embeddings_640x256.npy"
)

OUTPUT_DIR = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7"
)

OUTPUT_DATASET = os.path.join(
    OUTPUT_DIR,
    "step7F_final_multimodal_dataset_640.csv"
)

OUTPUT_REPORT = os.path.join(
    OUTPUT_DIR,
    "step7F_disease_label_verification.txt"
)


# =============================================================================
# 2. EXPECTED DISEASE CLASSES
# =============================================================================

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

CLASS_TO_INDEX = {
    name: idx
    for idx, name in enumerate(EXPECTED_CLASSES)
}


# =============================================================================
# 3. CHECK INPUT FILES
# =============================================================================

print("\n[1] CHECKING INPUT FILES")
print("-" * 80)

required_files = [
    IMAGE_INDEX,
    IMAGE_EMBEDDINGS,
    SATELLITE_EMBEDDINGS
]

for path in required_files:

    print(path)

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"\n❌ Required file not found:\n{path}"
        )

    print("✓ Exists")


# =============================================================================
# 4. LOAD IMAGE INDEX
# =============================================================================

print("\n[2] LOADING IMAGE INDEX")
print("-" * 80)

df = pd.read_csv(
    IMAGE_INDEX
)

print("Records:", len(df))

if len(df) != 640:

    raise RuntimeError(
        f"Expected 640 records, found {len(df)}"
    )

print("✓ 640 image records loaded")


# =============================================================================
# 5. LOAD EMBEDDINGS
# =============================================================================

print("\n[3] LOADING EMBEDDINGS")
print("-" * 80)

image_embeddings = np.load(
    IMAGE_EMBEDDINGS
)

satellite_embeddings = np.load(
    SATELLITE_EMBEDDINGS
)

print(
    "Image embeddings:",
    image_embeddings.shape
)

print(
    "Satellite embeddings:",
    satellite_embeddings.shape
)

if image_embeddings.shape != (640, 1792):

    raise RuntimeError(
        f"Unexpected image embedding shape: "
        f"{image_embeddings.shape}"
    )

if satellite_embeddings.shape != (640, 256):

    raise RuntimeError(
        f"Unexpected satellite embedding shape: "
        f"{satellite_embeddings.shape}"
    )

print("✓ Embedding shapes verified")


# =============================================================================
# 6. EXTRACT DISEASE LABEL FROM IMAGE PATH
# =============================================================================

print("\n[4] RECOVERING DISEASE LABELS")
print("-" * 80)

def get_disease_label(image_path):

    if not isinstance(image_path, str):

        return None

    normalized = os.path.normpath(
        image_path
    )

    parts = normalized.split(
        os.sep
    )

    # Find the folder immediately after "gps"
    # Example:
    #
    # .../gps/blast/image.jpg
    #
    # → blast

    for i, part in enumerate(parts):

        if part.lower() == "gps":

            if i + 1 < len(parts):

                return parts[i + 1]

    return None


df["disease_label"] = (
    df["image_path"]
    .apply(get_disease_label)
)


# =============================================================================
# 7. CHECK MISSING LABELS
# =============================================================================

missing_labels = df[
    df["disease_label"].isna()
].copy()

print(
    "Missing disease labels:",
    len(missing_labels)
)

if len(missing_labels) > 0:

    print("\n❌ Images without disease labels:")

    print(
        missing_labels[
            [
                "image_name",
                "image_path"
            ]
        ].to_string(index=False)
    )

    raise RuntimeError(
        "Some images do not have recoverable disease labels."
    )

print("✓ All 640 images have disease labels")


# =============================================================================
# 8. VERIFY LABEL NAMES
# =============================================================================

print("\n[5] VERIFYING DISEASE CLASS NAMES")
print("-" * 80)

found_classes = sorted(
    df["disease_label"]
    .unique()
)

print("Classes found:")
for cls in found_classes:
    print("  ", cls)


unknown_classes = [
    cls
    for cls in found_classes
    if cls not in EXPECTED_CLASSES
]

if unknown_classes:

    print("\n❌ UNKNOWN DISEASE CLASSES:")
    print(unknown_classes)

    raise RuntimeError(
        "Unknown disease class detected."
    )

print("\n✓ All disease labels belong to the expected 13 classes")


# =============================================================================
# 9. CHECK WHETHER ALL 13 CLASSES EXIST
# =============================================================================

missing_classes = [
    cls
    for cls in EXPECTED_CLASSES
    if cls not in found_classes
]

if missing_classes:

    print("\n⚠ Classes with zero images:")
    print(missing_classes)

else:

    print("✓ All 13 disease classes are represented")


# =============================================================================
# 10. DISEASE DISTRIBUTION
# =============================================================================

print("\n[6] DISEASE DISTRIBUTION")
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
    "\nTotal labelled images:",
    class_counts.sum()
)


# =============================================================================
# 11. CREATE NUMERICAL CLASS INDEX
# =============================================================================

print("\n[7] CREATING CLASS INDICES")
print("-" * 80)

df["disease_class_index"] = (
    df["disease_label"]
    .map(CLASS_TO_INDEX)
)

if df["disease_class_index"].isna().any():

    raise RuntimeError(
        "Some disease labels could not be converted "
        "to class indices."
    )

df["disease_class_index"] = (
    df["disease_class_index"]
    .astype(int)
)

print("✓ Disease class indices created")

print("\nClass mapping:")

for idx, cls in enumerate(EXPECTED_CLASSES):

    count = (
        df["disease_class_index"]
        == idx
    ).sum()

    print(
        f"{idx:2d} → {cls:30s} : {count}"
    )


# =============================================================================
# 12. VERIFY IMAGE EMBEDDING INDEX
# =============================================================================

print("\n[8] VERIFYING IMAGE EMBEDDING INDEX")
print("-" * 80)

expected_image_indices = np.arange(
    640
)

actual_image_indices = (
    df["image_embedding_index"]
    .to_numpy()
)

if not np.array_equal(
    actual_image_indices,
    expected_image_indices
):

    raise RuntimeError(
        "Image embedding index order is invalid."
    )

print("✓ Image embedding indices = 0–639")


# =============================================================================
# 13. VERIFY SATELLITE FIELD INFORMATION
# =============================================================================

print("\n[9] VERIFYING SATELLITE FIELD MAPPING")
print("-" * 80)

required_mapping_columns = [
    "nearest_satellite_field",
    "satellite_embedding_index"
]

for col in required_mapping_columns:

    if col not in df.columns:

        raise RuntimeError(
            f"Missing column: {col}"
        )

    if df[col].isna().any():

        raise RuntimeError(
            f"Missing values found in {col}"
        )

print("✓ Satellite field information present")


# =============================================================================
# 14. SATELLITE INDEX RANGE
# =============================================================================

sat_indices = (
    df["satellite_embedding_index"]
    .astype(int)
    .to_numpy()
)

print(
    "Minimum satellite index:",
    sat_indices.min()
)

print(
    "Maximum satellite index:",
    sat_indices.max()
)

if sat_indices.min() < 0:

    raise RuntimeError(
        "Negative satellite embedding index."
    )

if sat_indices.max() >= 58:

    raise RuntimeError(
        "Satellite embedding index exceeds 57."
    )

print("✓ Satellite indices valid")


# =============================================================================
# 15. BUILD FINAL MULTIMODAL DATASET
# =============================================================================

print("\n[10] BUILDING FINAL MULTIMODAL DATASET")
print("-" * 80)

df["image_embedding_file"] = (
    os.path.basename(
        IMAGE_EMBEDDINGS
    )
)

df["satellite_embedding_file"] = (
    os.path.basename(
        SATELLITE_EMBEDDINGS
    )
)

df["image_embedding_dimension"] = 1792
df["satellite_embedding_dimension"] = 256

# Add direct row index for paired satellite embedding
df["paired_satellite_embedding_index"] = (
    np.arange(640)
)

print("✓ Multimodal metadata assembled")


# =============================================================================
# 16. FINAL DATASET VALIDATION
# =============================================================================

print("\n[11] FINAL MULTIMODAL VALIDATION")
print("-" * 80)

checks = {
    "Image records":
        len(df) == 640,

    "Image embeddings":
        image_embeddings.shape == (640, 1792),

    "Satellite embeddings":
        satellite_embeddings.shape == (640, 256),

    "Image index":
        np.array_equal(
            df["image_embedding_index"].to_numpy(),
            np.arange(640)
        ),

    "Disease labels":
        df["disease_label"].notna().all(),

    "Disease class indices":
        df["disease_class_index"].notna().all(),

    "Satellite field":
        df["nearest_satellite_field"].notna().all(),

    "Satellite indices":
        df["satellite_embedding_index"].notna().all(),

    "Image NaN":
        not np.isnan(image_embeddings).any(),

    "Image Inf":
        not np.isinf(image_embeddings).any(),

    "Satellite NaN":
        not np.isnan(satellite_embeddings).any(),

    "Satellite Inf":
        not np.isinf(satellite_embeddings).any()
}

for name, result in checks.items():

    print(
        f"{name:25s}: "
        f"{'PASS' if result else 'FAIL'}"
    )

if not all(checks.values()):

    raise RuntimeError(
        "❌ Final multimodal validation failed."
    )

print("\n✓ ALL MULTIMODAL CHECKS PASSED")


# =============================================================================
# 17. SAVE FINAL METADATA
# =============================================================================

print("\n[12] SAVING FINAL MULTIMODAL METADATA")
print("-" * 80)

df.to_csv(
    OUTPUT_DATASET,
    index=False
)

print("✓ Saved:")
print(OUTPUT_DATASET)


# =============================================================================
# 18. CREATE VERIFICATION REPORT
# =============================================================================

report = f"""
STEP 7F — DISEASE LABEL VERIFICATION
======================================

FINAL DATASET
-------------

Total images:
640

Image embedding dimension:
1792

Satellite embedding dimension:
256

Disease classes:
13


DISEASE CLASSES
---------------

"""

for idx, cls in enumerate(EXPECTED_CLASSES):

    count = int(
        class_counts.loc[cls]
    )

    report += (
        f"{idx:2d} | "
        f"{cls:30s} | "
        f"{count} images\n"
    )


report += f"""

EMBEDDINGS
----------

Image embeddings:
{image_embeddings.shape}

Satellite embeddings:
{satellite_embeddings.shape}

Image NaN:
{np.isnan(image_embeddings).sum()}

Image Inf:
{np.isinf(image_embeddings).sum()}

Satellite NaN:
{np.isnan(satellite_embeddings).sum()}

Satellite Inf:
{np.isinf(satellite_embeddings).sum()}


SATELLITE FIELDS
----------------

Unique satellite fields:
{df["nearest_satellite_field"].nunique()}

Minimum satellite index:
{sat_indices.min()}

Maximum satellite index:
{sat_indices.max()}


STATUS
------

PASS

All 640 image records have valid disease labels
and valid satellite mappings.
"""


with open(
    OUTPUT_REPORT,
    "w"
) as f:

    f.write(report)


print("\n✓ Verification report saved:")
print(OUTPUT_REPORT)


# =============================================================================
# 19. FINAL STATUS
# =============================================================================

print("\n")
print("=" * 80)
print("STEP 7F — COMPLETE")
print("=" * 80)

print("""
✓ 640 images verified
✓ Disease labels recovered
✓ 13-class mapping verified
✓ Disease class indices created
✓ Image embeddings verified
✓ Satellite embeddings verified
✓ Image ↔ satellite mapping verified
✓ NaN = 0
✓ Inf = 0
✓ Final multimodal metadata saved

NEXT:
Step 7G — FINAL MULTIMODAL DATASET CHECK
Then Cross-Attention Fusion.
""")

print("=" * 80)