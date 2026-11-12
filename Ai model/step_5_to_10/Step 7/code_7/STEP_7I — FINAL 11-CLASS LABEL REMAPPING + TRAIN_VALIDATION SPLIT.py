# =============================================================================
# STEP 7I — FINAL 11-CLASS LABEL REMAPPING + TRAIN/VALIDATION SPLIT
# =============================================================================

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

print("=" * 80)
print("STEP 7I — FINAL 11-CLASS LABEL REMAPPING + TRAIN/VALIDATION SPLIT")
print("=" * 80)

# =============================================================================
# 1. PATHS
# =============================================================================

BASE_DIR = "/content/drive/MyDrive/final year project/Real_world_test/Step 7"

DATASET_FILE = os.path.join(
    BASE_DIR,
    "step7F_final_multimodal_dataset_640.csv"
)

IMAGE_EMBEDDINGS_FILE = os.path.join(
    BASE_DIR,
    "step7_FINAL_image_embeddings_1792.npy"
)

SATELLITE_EMBEDDINGS_FILE = os.path.join(
    BASE_DIR,
    "step7E_paired_satellite_embeddings_640x256.npy"
)

OUTPUT_DATASET = os.path.join(
    BASE_DIR,
    "step7I_final_11class_multimodal_dataset.csv"
)

OUTPUT_TRAIN = os.path.join(
    BASE_DIR,
    "step7I_train_indices.npy"
)

OUTPUT_VAL = os.path.join(
    BASE_DIR,
    "step7I_val_indices.npy"
)

OUTPUT_LABELS = os.path.join(
    BASE_DIR,
    "step7I_final_11class_mapping.txt"
)

# =============================================================================
# 2. CHECK FILES
# =============================================================================

print("\n[1] CHECKING REQUIRED FILES")
print("-" * 80)

required_files = [
    DATASET_FILE,
    IMAGE_EMBEDDINGS_FILE,
    SATELLITE_EMBEDDINGS_FILE
]

for file_path in required_files:

    print(file_path)

    if os.path.exists(file_path):
        print("✓ Exists")
    else:
        raise FileNotFoundError(
            f"\n❌ Required file not found:\n{file_path}"
        )

# =============================================================================
# 3. LOAD DATA
# =============================================================================

print("\n[2] LOADING DATA")
print("-" * 80)

df = pd.read_csv(DATASET_FILE)

image_embeddings = np.load(
    IMAGE_EMBEDDINGS_FILE
)

satellite_embeddings = np.load(
    SATELLITE_EMBEDDINGS_FILE
)

print("Dataset shape:", df.shape)
print("Image embeddings:", image_embeddings.shape)
print("Satellite embeddings:", satellite_embeddings.shape)

# =============================================================================
# 4. BASIC VALIDATION
# =============================================================================

print("\n[3] BASIC DATA VALIDATION")
print("-" * 80)

if len(df) != 640:
    raise ValueError(
        f"Expected 640 dataset records, found {len(df)}"
    )

if image_embeddings.shape != (640, 1792):
    raise ValueError(
        f"Expected image embeddings (640,1792), "
        f"found {image_embeddings.shape}"
    )

if satellite_embeddings.shape != (640, 256):
    raise ValueError(
        f"Expected satellite embeddings (640,256), "
        f"found {satellite_embeddings.shape}"
    )

print("✓ Dataset = 640")
print("✓ Image embeddings = (640, 1792)")
print("✓ Satellite embeddings = (640, 256)")

# =============================================================================
# 5. FINAL 11-CLASS DEFINITION
# =============================================================================

print("\n[4] DEFINING FINAL 11 CLASSES")
print("-" * 80)

FINAL_CLASSES = [
    "bacterial_leaf_blight",
    "bacterial_leaf_streak",
    "bacterial_panicle_blight",
    "blast",
    "brown_spot",
    "dead_heart",
    "downy_mildew",
    "hispa",
    "leaf_scald",
    "sheath_blight",
    "tungro"
]

class_to_index = {
    class_name: index
    for index, class_name in enumerate(FINAL_CLASSES)
}

index_to_class = {
    index: class_name
    for class_name, index in class_to_index.items()
}

for index, class_name in enumerate(FINAL_CLASSES):
    print(f"{index:2d} → {class_name}")

# =============================================================================
# 6. CHECK DATASET LABELS
# =============================================================================

print("\n[5] CHECKING DATASET LABELS")
print("-" * 80)

unique_labels = sorted(
    df["disease_label"].dropna().unique()
)

print("Labels found in dataset:")

for label in unique_labels:
    print(" ", label)

unexpected_labels = [
    label
    for label in unique_labels
    if label not in FINAL_CLASSES
]

if unexpected_labels:

    print("\n❌ Unexpected labels found:")

    for label in unexpected_labels:
        print(" ", label)

    raise ValueError(
        "Dataset contains labels outside the final 11-class configuration."
    )

print("\n✓ All dataset labels belong to the final 11 classes")

# =============================================================================
# 7. REMOVE ZERO-SAMPLE CLASSES FROM LABEL SPACE
# =============================================================================

print("\n[6] ZERO-SAMPLE CLASS CHECK")
print("-" * 80)

zero_sample_classes = []

for class_name in FINAL_CLASSES:

    count = int(
        (df["disease_label"] == class_name).sum()
    )

    print(f"{class_name:30s} : {count}")

    if count == 0:
        zero_sample_classes.append(class_name)

if zero_sample_classes:
    raise ValueError(
        f"Unexpected zero-sample classes in final 11-class list: "
        f"{zero_sample_classes}"
    )

print("\n✓ All 11 classes contain samples")

# =============================================================================
# 8. CREATE COMPACT NUMERIC LABELS
# =============================================================================

print("\n[7] CREATING NUMERIC LABELS")
print("-" * 80)

df["label_11class"] = df["disease_label"].map(
    class_to_index
)

# Check for missing mappings
if df["label_11class"].isna().any():

    bad_rows = df[
        df["label_11class"].isna()
    ]

    print(bad_rows[
        ["disease_label"]
    ])

    raise ValueError(
        "Some disease labels could not be mapped."
    )

df["label_11class"] = (
    df["label_11class"]
    .astype(int)
)

print("✓ Numeric labels created")

# =============================================================================
# 9. VERIFY LABEL RANGE
# =============================================================================

print("\n[8] VERIFYING LABEL RANGE")
print("-" * 80)

minimum_label = int(
    df["label_11class"].min()
)

maximum_label = int(
    df["label_11class"].max()
)

print("Minimum label:", minimum_label)
print("Maximum label:", maximum_label)

if minimum_label != 0 or maximum_label != 10:
    raise ValueError(
        "Final labels are not in the expected range 0–10."
    )

print("✓ Labels correctly range from 0 to 10")

# =============================================================================
# 10. CLASS DISTRIBUTION
# =============================================================================

print("\n[9] FINAL CLASS DISTRIBUTION")
print("-" * 80)

class_counts = (
    df["label_11class"]
    .value_counts()
    .sort_index()
)

for index, count in class_counts.items():

    print(
        f"{index:2d} | "
        f"{index_to_class[index]:30s} | "
        f"{count:3d}"
    )

print("-" * 80)
print("Total:", int(class_counts.sum()))

# =============================================================================
# 11. STRATIFIED TRAIN / VALIDATION SPLIT
# =============================================================================

print("\n[10] CREATING STRATIFIED TRAIN / VALIDATION SPLIT")
print("-" * 80)

all_indices = np.arange(
    len(df)
)

labels = df["label_11class"].values

train_indices, val_indices = train_test_split(
    all_indices,
    test_size=0.20,
    random_state=42,
    stratify=labels
)

train_indices = np.sort(
    train_indices
)

val_indices = np.sort(
    val_indices
)

print("Total samples:", len(all_indices))
print("Training samples:", len(train_indices))
print("Validation samples:", len(val_indices))

# =============================================================================
# 12. VERIFY SPLIT
# =============================================================================

print("\n[11] VERIFYING TRAIN / VALIDATION SPLIT")
print("-" * 80)

if len(train_indices) + len(val_indices) != len(df):
    raise ValueError(
        "Train + validation samples do not equal total dataset."
    )

intersection = np.intersect1d(
    train_indices,
    val_indices
)

if len(intersection) != 0:
    raise ValueError(
        "Data leakage detected: train and validation indices overlap."
    )

print("✓ No overlap between train and validation")

# =============================================================================
# 13. CLASS DISTRIBUTION IN TRAINING SET
# =============================================================================

print("\n[12] TRAINING CLASS DISTRIBUTION")
print("-" * 80)

train_labels = labels[
    train_indices
]

train_counts = (
    pd.Series(train_labels)
    .value_counts()
    .sort_index()
)

for index in range(11):

    count = int(
        train_counts.get(index, 0)
    )

    print(
        f"{index:2d} | "
        f"{index_to_class[index]:30s} | "
        f"{count:3d}"
    )

# =============================================================================
# 14. CLASS DISTRIBUTION IN VALIDATION SET
# =============================================================================

print("\n[13] VALIDATION CLASS DISTRIBUTION")
print("-" * 80)

val_labels = labels[
    val_indices
]

val_counts = (
    pd.Series(val_labels)
    .value_counts()
    .sort_index()
)

for index in range(11):

    count = int(
        val_counts.get(index, 0)
    )

    print(
        f"{index:2d} | "
        f"{index_to_class[index]:30s} | "
        f"{count:3d}"
    )

# =============================================================================
# 15. ADD SPLIT INFORMATION TO DATASET
# =============================================================================

print("\n[14] ADDING SPLIT INFORMATION")
print("-" * 80)

df["split"] = "unused"

df.loc[
    train_indices,
    "split"
] = "train"

df.loc[
    val_indices,
    "split"
] = "validation"

print(
    df["split"].value_counts()
)

# =============================================================================
# 16. FINAL MULTIMODAL CONSISTENCY CHECK
# =============================================================================

print("\n[15] FINAL MULTIMODAL CONSISTENCY CHECK")
print("-" * 80)

if len(df) != image_embeddings.shape[0]:
    raise ValueError(
        "Dataset and image embedding count mismatch."
    )

if len(df) != satellite_embeddings.shape[0]:
    raise ValueError(
        "Dataset and satellite embedding count mismatch."
    )

if df["label_11class"].isna().any():
    raise ValueError(
        "NaN labels detected."
    )

if np.isnan(image_embeddings).any():
    raise ValueError(
        "NaN found in image embeddings."
    )

if np.isnan(satellite_embeddings).any():
    raise ValueError(
        "NaN found in satellite embeddings."
    )

if np.isinf(image_embeddings).any():
    raise ValueError(
        "Inf found in image embeddings."
    )

if np.isinf(satellite_embeddings).any():
    raise ValueError(
        "Inf found in satellite embeddings."
    )

print("✓ Dataset count = 640")
print("✓ Image embeddings = 640")
print("✓ Satellite embeddings = 640")
print("✓ Labels valid")
print("✓ No NaN")
print("✓ No Inf")
print("✓ Train/validation split valid")

# =============================================================================
# 17. SAVE FINAL DATASET
# =============================================================================

print("\n[16] SAVING OUTPUT FILES")
print("-" * 80)

df.to_csv(
    OUTPUT_DATASET,
    index=False
)

np.save(
    OUTPUT_TRAIN,
    train_indices
)

np.save(
    OUTPUT_VAL,
    val_indices
)

# =============================================================================
# 18. SAVE CLASS MAPPING REPORT
# =============================================================================

with open(
    OUTPUT_LABELS,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "STEP 7I — FINAL 11-CLASS LABEL MAPPING\n"
    )

    f.write("=" * 70 + "\n\n")

    f.write(
        "Final classifier configuration: 11 classes\n"
    )

    f.write(
        "Dataset size: 640\n"
    )

    f.write(
        "Training samples: "
        f"{len(train_indices)}\n"
    )

    f.write(
        "Validation samples: "
        f"{len(val_indices)}\n\n"
    )

    f.write("CLASS MAPPING\n")
    f.write("-" * 70 + "\n")

    for index, class_name in enumerate(FINAL_CLASSES):

        total = int(
            class_counts.get(index, 0)
        )

        train_count = int(
            train_counts.get(index, 0)
        )

        val_count = int(
            val_counts.get(index, 0)
        )

        f.write(
            f"{index:2d} -> {class_name:30s} "
            f"total={total:3d} "
            f"train={train_count:3d} "
            f"val={val_count:3d}\n"
        )

    f.write("\n")
    f.write("Split configuration:\n")
    f.write("Validation ratio: 20%\n")
    f.write("Random seed: 42\n")
    f.write("Stratified split: YES\n")

# =============================================================================
# 19. FINAL SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("STEP 7I — COMPLETE")
print("=" * 80)

print("\n✓ Final classifier configuration: 11 classes")
print("✓ 640 multimodal records")
print("✓ Labels remapped to 0–10")
print("✓ Stratified train/validation split created")
print(f"✓ Training samples: {len(train_indices)}")
print(f"✓ Validation samples: {len(val_indices)}")
print("✓ No train/validation overlap")
print("✓ All 11 classes represented")
print("✓ No NaN / Inf detected")

print("\nSaved files:")
print(OUTPUT_DATASET)
print(OUTPUT_TRAIN)
print(OUTPUT_VAL)
print(OUTPUT_LABELS)

print("\n" + "=" * 80)
print("DO NOT START TRAINING YET.")
print("Send me the complete STEP 7I output first.")
print("=" * 80)