# =============================================================================
# STEP_7D — FINAL EFFICIENTNET-B4 IMAGE EMBEDDING GENERATION
# =============================================================================
# Input:
#   641 mapping records
#
# After validation:
#   1 missing duplicate record removed
#   640 valid unique images
#
# Output:
#   640 × 1792 image embeddings
# =============================================================================

import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from torch.utils.data import Dataset, DataLoader
from PIL import Image
from torchvision import models, transforms


# =============================================================================
# 0. START
# =============================================================================

print("=" * 80)
print("STEP 7D — FINAL IMAGE EMBEDDING GENERATION")
print("=" * 80)


# =============================================================================
# 1. PATHS
# =============================================================================

CHECKPOINT = (
    "/content/drive/MyDrive/final year project/"
    "models/dl/efficientnet_b4_phaseC_best.pth"
)

MAPPING_CSV = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7/"
    "step7_FINAL_image_field_satellite_mapping.csv"
)

OUTPUT_DIR = (
    "/content/drive/MyDrive/final year project/"
    "Real_world_test/Step 7"
)

OUTPUT_EMBEDDINGS = os.path.join(
    OUTPUT_DIR,
    "step7_FINAL_image_embeddings_1792.npy"
)

OUTPUT_INDEX = os.path.join(
    OUTPUT_DIR,
    "step7_FINAL_image_embedding_index.csv"
)

OUTPUT_REPORT = os.path.join(
    OUTPUT_DIR,
    "step7D_image_embedding_verification.txt"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =============================================================================
# 2. CHECK INPUT FILES
# =============================================================================

print("\n[1] CHECKING INPUT FILES")
print("-" * 80)

if not os.path.exists(CHECKPOINT):
    raise FileNotFoundError(
        f"\n❌ EfficientNet checkpoint not found:\n{CHECKPOINT}"
    )

if not os.path.exists(MAPPING_CSV):
    raise FileNotFoundError(
        f"\n❌ Mapping CSV not found:\n{MAPPING_CSV}"
    )

print("✓ EfficientNet-B4 checkpoint found")
print("✓ Image mapping CSV found")


# =============================================================================
# 3. LOAD MAPPING
# =============================================================================

print("\n[2] LOADING IMAGE MAPPING")
print("-" * 80)

df = pd.read_csv(MAPPING_CSV)

print("Original mapping records:", len(df))

required_columns = [
    "image_name",
    "image_path",
    "nearest_satellite_field",
    "satellite_embedding_index"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:

    raise RuntimeError(
        f"Missing required columns:\n{missing_columns}"
    )

print("✓ Required columns available")


# =============================================================================
# 4. CHECK ALL IMAGE PATHS
# =============================================================================

print("\n[3] VERIFYING IMAGE FILES")
print("-" * 80)

df["file_exists"] = df["image_path"].apply(
    lambda x:
        isinstance(x, str)
        and os.path.isfile(x)
)

missing_df = df[
    ~df["file_exists"]
].copy()

print("Total records:", len(df))
print("Existing image files:", df["file_exists"].sum())
print("Missing image files:", len(missing_df))


# =============================================================================
# 5. SHOW MISSING RECORDS
# =============================================================================

if len(missing_df) > 0:

    print("\nMissing image records:")
    print("-" * 80)

    print(
        missing_df[
            [
                "image_name",
                "image_path",
                "nearest_satellite_field",
                "satellite_embedding_index"
            ]
        ].to_string(index=False)
    )


# =============================================================================
# 6. REMOVE ONLY MISSING FILE RECORDS
# =============================================================================

print("\n[4] RECTIFYING INVALID IMAGE RECORDS")
print("-" * 80)

before_count = len(df)

df = df[
    df["file_exists"]
].copy()

df.drop(
    columns=["file_exists"],
    inplace=True
)

after_missing_removal = len(df)

print(
    f"Removed missing records: "
    f"{before_count - after_missing_removal}"
)

print(
    f"Remaining valid records: "
    f"{after_missing_removal}"
)


# =============================================================================
# 7. CHECK DUPLICATE IMAGE NAMES
# =============================================================================

print("\n[5] CHECKING DUPLICATE IMAGE NAMES")
print("-" * 80)

duplicate_mask = df.duplicated(
    subset=["image_name"],
    keep=False
)

duplicate_df = df[
    duplicate_mask
].copy()

print(
    "Duplicate records among existing files:",
    len(duplicate_df)
)


# =============================================================================
# 8. HANDLE EXISTING DUPLICATES
# =============================================================================

if len(duplicate_df) > 0:

    print("\nDuplicate existing images found:")

    print(
        duplicate_df[
            [
                "image_name",
                "image_path",
                "nearest_satellite_field",
                "satellite_embedding_index"
            ]
        ].to_string(index=False)
    )

    # Check whether duplicate image names have
    # conflicting satellite mappings.

    conflict_check = (
        duplicate_df
        .groupby("image_name")
        .agg(
            satellite_fields=(
                "nearest_satellite_field",
                "nunique"
            ),
            embedding_indices=(
                "satellite_embedding_index",
                "nunique"
            ),
            paths=(
                "image_path",
                "nunique"
            )
        )
    )

    real_conflicts = conflict_check[
        (conflict_check["satellite_fields"] > 1)
        |
        (conflict_check["embedding_indices"] > 1)
    ]

    if len(real_conflicts) > 0:

        print("\n❌ REAL DUPLICATE MAPPING CONFLICT")

        print(real_conflicts)

        raise RuntimeError(
            "Existing duplicate image names have "
            "different satellite mappings."
        )

    # Same satellite mapping.
    # Keep only one physical image record.

    before_duplicate_removal = len(df)

    df = df.drop_duplicates(
        subset=["image_name"],
        keep="first"
    ).copy()

    removed_duplicates = (
        before_duplicate_removal - len(df)
    )

    print(
        f"\n✓ Duplicate records removed: "
        f"{removed_duplicates}"
    )

else:

    print("✓ No existing duplicate image names")


# =============================================================================
# 9. FINAL IMAGE COUNT
# =============================================================================

print("\n[6] FINAL IMAGE COUNT")
print("-" * 80)

final_image_count = len(df)

print(
    "Final valid unique images:",
    final_image_count
)

# IMPORTANT:
# The correct number is 640, not 641.
#
# Original:
#   641 mapping records
#
# One record:
#   missing physical image
#
# Final:
#   640 valid unique images

if final_image_count != 640:

    raise RuntimeError(
        f"""
❌ Unexpected final image count.

Expected: 640
Found:    {final_image_count}

STOP — embeddings will NOT be generated.
"""
    )

print("✓ 640 valid unique images confirmed")


# =============================================================================
# 10. VERIFY SATELLITE EMBEDDING INDICES
# =============================================================================

print("\n[7] VERIFYING SATELLITE EMBEDDING INDICES")
print("-" * 80)

if df["satellite_embedding_index"].isna().any():

    raise RuntimeError(
        "Some images have missing satellite embedding index."
    )

df["satellite_embedding_index"] = (
    df["satellite_embedding_index"]
    .astype(int)
)

print(
    "Minimum satellite embedding index:",
    df["satellite_embedding_index"].min()
)

print(
    "Maximum satellite embedding index:",
    df["satellite_embedding_index"].max()
)

print("✓ Satellite embedding indices valid")


# =============================================================================
# 11. LOAD EFFICIENTNET-B4 CHECKPOINT
# =============================================================================

print("\n[8] LOADING EFFICIENTNET-B4 PHASE-C")
print("-" * 80)

checkpoint = torch.load(
    CHECKPOINT,
    map_location="cpu"
)

print(
    "Checkpoint epoch:",
    checkpoint.get("epoch")
)

print(
    "Best validation accuracy:",
    checkpoint.get("best_val_accuracy")
)

print(
    "Number of classes:",
    checkpoint.get("num_classes")
)

state_dict = checkpoint[
    "model_state_dict"
]


# =============================================================================
# 12. CREATE EFFICIENTNET-B4
# =============================================================================

model = models.efficientnet_b4(
    weights=None,
    num_classes=13
)

print("\n✓ EfficientNet-B4 architecture created")


# =============================================================================
# 13. LOAD ONLY FEATURE WEIGHTS
# =============================================================================
# Classifier mismatch does NOT matter here because we only
# need the 1792-D feature representation.
# =============================================================================

feature_state_dict = {
    key: value
    for key, value in state_dict.items()
    if not key.startswith("classifier.")
}

model_state = model.state_dict()

for key, value in feature_state_dict.items():

    if key not in model_state:

        raise RuntimeError(
            f"Unexpected feature key: {key}"
        )

    if model_state[key].shape != value.shape:

        raise RuntimeError(
            f"""
Shape mismatch:

Key: {key}
Model: {model_state[key].shape}
Checkpoint: {value.shape}
"""
        )

    model_state[key] = value


model.load_state_dict(
    model_state,
    strict=True
)

print("✓ Phase-C feature weights loaded")


# =============================================================================
# 14. CREATE FEATURE EXTRACTOR
# =============================================================================

print("\n[9] CREATING 1792-D FEATURE EXTRACTOR")
print("-" * 80)

feature_extractor = nn.Sequential(
    model.features,
    model.avgpool,
    nn.Flatten()
)

feature_extractor.eval()

print("✓ Feature extractor created")


# =============================================================================
# 15. DEVICE
# =============================================================================

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

feature_extractor = (
    feature_extractor
    .to(device)
)

print("Device:", device)


# =============================================================================
# 16. IMAGE PREPROCESSING
# =============================================================================

print("\n[10] IMAGE PREPROCESSING")
print("-" * 80)

transform = transforms.Compose([
    transforms.Resize(
        (380, 380)
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[
            0.485,
            0.456,
            0.406
        ],

        std=[
            0.229,
            0.224,
            0.225
        ]
    )
])

print("✓ Resize: 380 × 380")
print("✓ RGB conversion")
print("✓ ImageNet normalization")


# =============================================================================
# 17. DATASET
# =============================================================================

class PaddyImageDataset(Dataset):

    def __init__(
        self,
        dataframe,
        transform=None
    ):

        self.df = (
            dataframe
            .reset_index(drop=True)
        )

        self.transform = transform

    def __len__(self):

        return len(self.df)

    def __getitem__(self, idx):

        row = self.df.iloc[idx]

        image_path = row[
            "image_path"
        ]

        try:

            image = Image.open(
                image_path
            ).convert("RGB")

        except Exception as e:

            raise RuntimeError(
                f"""
Failed to load image.

Index:
{idx}

Image:
{image_path}

Error:
{e}
"""
            )

        if self.transform:

            image = self.transform(
                image
            )

        return image, idx


dataset = PaddyImageDataset(
    df,
    transform=transform
)

print("\n✓ Dataset created")
print("Dataset size:", len(dataset))


# =============================================================================
# 18. DATALOADER
# =============================================================================

loader = DataLoader(
    dataset,
    batch_size=16,
    shuffle=False,
    num_workers=2,
    pin_memory=torch.cuda.is_available()
)

print("\n[11] DATALOADER")
print("-" * 80)

print("Batch size:", 16)
print("Number of batches:", len(loader))
print("Shuffle:", False)


# =============================================================================
# 19. GENERATE EMBEDDINGS
# =============================================================================

print("\n[12] GENERATING IMAGE EMBEDDINGS")
print("-" * 80)

all_embeddings = []

feature_extractor.eval()

with torch.no_grad():

    for batch_number, (
        images,
        indices
    ) in enumerate(loader):

        images = images.to(
            device,
            non_blocking=True
        )

        batch_embeddings = (
            feature_extractor(
                images
            )
        )

        batch_embeddings = (
            batch_embeddings
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        all_embeddings.append(
            batch_embeddings
        )

        processed = min(
            (batch_number + 1) * 16,
            final_image_count
        )

        print(
            f"Processed: "
            f"{processed:3d} / "
            f"{final_image_count}"
        )


# =============================================================================
# 20. COMBINE ALL EMBEDDINGS
# =============================================================================

print("\n[13] COMBINING EMBEDDINGS")
print("-" * 80)

embeddings = np.concatenate(
    all_embeddings,
    axis=0
).astype(np.float32)

print(
    "Final embedding shape:",
    embeddings.shape
)


# =============================================================================
# 21. STRICT SHAPE VALIDATION
# =============================================================================

print("\n[14] SHAPE VALIDATION")
print("-" * 80)

expected_shape = (
    640,
    1792
)

if embeddings.shape != expected_shape:

    raise RuntimeError(
        f"""
❌ Embedding shape mismatch.

Expected:
{expected_shape}

Found:
{embeddings.shape}
"""
    )

print(
    "✓ Shape:",
    embeddings.shape
)


# =============================================================================
# 22. NUMERICAL VALIDATION
# =============================================================================

print("\n[15] NUMERICAL VALIDATION")
print("-" * 80)

nan_count = int(
    np.isnan(embeddings).sum()
)

inf_count = int(
    np.isinf(embeddings).sum()
)

print("NaN values:", nan_count)
print("Infinite values:", inf_count)

if nan_count != 0:

    raise RuntimeError(
        "❌ NaN values detected."
    )

if inf_count != 0:

    raise RuntimeError(
        "❌ Infinite values detected."
    )

print("✓ No NaN")
print("✓ No Inf")


# =============================================================================
# 23. EMBEDDING STATISTICS
# =============================================================================

print("\n[16] EMBEDDING STATISTICS")
print("-" * 80)

embedding_mean = float(
    embeddings.mean()
)

embedding_std = float(
    embeddings.std()
)

embedding_min = float(
    embeddings.min()
)

embedding_max = float(
    embeddings.max()
)

print("Mean:", embedding_mean)
print("Std :", embedding_std)
print("Min :", embedding_min)
print("Max :", embedding_max)


# =============================================================================
# 24. SAVE EMBEDDINGS
# =============================================================================

print("\n[17] SAVING IMAGE EMBEDDINGS")
print("-" * 80)

np.save(
    OUTPUT_EMBEDDINGS,
    embeddings
)

print("✓ Saved:")
print(
    OUTPUT_EMBEDDINGS
)


# =============================================================================
# 25. CREATE EMBEDDING INDEX
# =============================================================================

print("\n[18] CREATING EMBEDDING INDEX")
print("-" * 80)

index_df = (
    df
    .reset_index(drop=True)
    .copy()
)

index_df.insert(
    0,
    "image_embedding_index",
    np.arange(
        len(index_df)
    )
)

index_df[
    "image_embedding_dimension"
] = 1792

index_df.to_csv(
    OUTPUT_INDEX,
    index=False
)

print("✓ Saved:")
print(
    OUTPUT_INDEX
)


# =============================================================================
# 26. FINAL VERIFICATION REPORT
# =============================================================================

report = f"""
STEP 7D — FINAL IMAGE EMBEDDING VERIFICATION
==============================================

INPUT
-----

EfficientNet checkpoint:
{CHECKPOINT}

Mapping file:
{MAPPING_CSV}


IMAGE VALIDATION
----------------

Original mapping records:
641

Missing image records removed:
1

Final valid unique images:
640


MODEL
-----

Architecture:
EfficientNet-B4

Checkpoint:
Phase-C

Number of classes:
13

Feature dimension:
1792

Training performed during Step 7D:
NO


EMBEDDINGS
----------

Shape:
{embeddings.shape}

dtype:
{embeddings.dtype}

NaN:
{nan_count}

Inf:
{inf_count}

Mean:
{embedding_mean}

Std:
{embedding_std}

Minimum:
{embedding_min}

Maximum:
{embedding_max}


OUTPUT
------

Embedding file:
{OUTPUT_EMBEDDINGS}

Index file:
{OUTPUT_INDEX}


STATUS
------

PASS

640 valid unique images successfully converted
to 1792-dimensional EfficientNet-B4 embeddings.
"""

with open(
    OUTPUT_REPORT,
    "w"
) as f:

    f.write(report)

print("\n✓ Verification report saved:")
print(
    OUTPUT_REPORT
)


# =============================================================================
# 27. FINAL STATUS
# =============================================================================

print("\n")
print("=" * 80)
print("STEP 7D — COMPLETE")
print("=" * 80)

print("""
✓ Original records              : 641
✓ Missing invalid record removed: 1
✓ Final valid unique images     : 640
✓ EfficientNet-B4 Phase-C       : USED
✓ Retraining                    : NO
✓ Image embedding dimension     : 1792
✓ Final embedding matrix        : (640, 1792)
✓ NaN                           : 0
✓ Inf                           : 0
✓ Embedding index CSV           : CREATED
✓ Verification report           : CREATED

NEXT STEP:
Verify the 640 image embeddings together with
their disease labels and satellite embeddings.

DO NOT START CROSS-ATTENTION TRAINING YET.
""")

print("=" * 80)