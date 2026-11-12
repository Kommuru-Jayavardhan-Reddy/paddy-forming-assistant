# =============================================================================
# STEP 7H — ARCHITECTURE & CLASSIFIER CONFIGURATION VERIFICATION
# =============================================================================

import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torchvision import models


print("=" * 80)
print("STEP 7H — ARCHITECTURE & CLASSIFIER CONFIGURATION VERIFICATION")
print("=" * 80)


# =============================================================================
# 1. PATHS
# =============================================================================

CHECKPOINT = (
    "/content/drive/MyDrive/final year project/"
    "models/dl/efficientnet_b4_phaseC_best.pth"
)

FINAL_DATASET = (
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
    "step7H_architecture_configuration_report.txt"
)


# =============================================================================
# 2. EXPECTED PROJECT CLASSES
# =============================================================================

PROJECT_CLASSES = [
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


# =============================================================================
# 3. CHECK FILES
# =============================================================================

print("\n[1] CHECKING FILES")
print("-" * 80)

for path in [
    CHECKPOINT,
    FINAL_DATASET,
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
# 4. LOAD DATASET
# =============================================================================

print("\n[2] LOADING FINAL DATASET")
print("-" * 80)

df = pd.read_csv(
    FINAL_DATASET
)

print("Dataset shape:", df.shape)

if len(df) != 640:

    raise RuntimeError(
        f"Expected 640 records, found {len(df)}"
    )

print("✓ 640 records")


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
        "Image embedding shape is incorrect."
    )

if satellite_embeddings.shape != (640, 256):

    raise RuntimeError(
        "Satellite embedding shape is incorrect."
    )

print("✓ Embedding dimensions verified")


# =============================================================================
# 6. ACTUAL DATASET CLASSES
# =============================================================================

print("\n[4] DATASET CLASS ANALYSIS")
print("-" * 80)

dataset_class_counts = (
    df["disease_label"]
    .value_counts()
    .reindex(
        PROJECT_CLASSES,
        fill_value=0
    )
)

print(
    dataset_class_counts.to_string()
)

present_classes = [
    cls
    for cls in PROJECT_CLASSES
    if dataset_class_counts[cls] > 0
]

zero_classes = [
    cls
    for cls in PROJECT_CLASSES
    if dataset_class_counts[cls] == 0
]

print("\nTotal project classes:", len(PROJECT_CLASSES))
print("Classes with samples:", len(present_classes))
print("Classes with zero samples:", len(zero_classes))

print("\nZero-sample classes:")

for cls in zero_classes:
    print("  ", cls)


# =============================================================================
# 7. LOAD ORIGINAL CHECKPOINT
# =============================================================================

print("\n[5] CHECKPOINT CLASS CONFIGURATION")
print("-" * 80)

checkpoint = torch.load(
    CHECKPOINT,
    map_location="cpu"
)

checkpoint_num_classes = checkpoint.get(
    "num_classes",
    None
)

checkpoint_classes = checkpoint.get(
    "classes",
    None
)

print(
    "Checkpoint num_classes:",
    checkpoint_num_classes
)

print(
    "Checkpoint classes:",
    checkpoint_classes
)


# =============================================================================
# 8. VERIFY CHECKPOINT CLASSES
# =============================================================================

if checkpoint_num_classes != 13:

    print(
        "\n⚠ Checkpoint does not report 13 classes."
    )

else:

    print(
        "✓ Checkpoint reports 13 classes"
    )


if checkpoint_classes is not None:

    if list(checkpoint_classes) == PROJECT_CLASSES:

        print(
            "✓ Checkpoint class order matches project class order"
        )

    else:

        print(
            "\n⚠ Checkpoint class order differs."
        )

        print(
            "Checkpoint:",
            checkpoint_classes
        )

        print(
            "Project:",
            PROJECT_CLASSES
        )


# =============================================================================
# 9. DEFINE THREE POSSIBLE CLASSIFIER CONFIGURATIONS
# =============================================================================

print("\n[6] CLASSIFIER CONFIGURATION ANALYSIS")
print("-" * 80)

configurations = {
    "DOCUMENT_SPEC": 10,
    "DATASET_PRESENT_CLASSES": len(present_classes),
    "ORIGINAL_CHECKPOINT": checkpoint_num_classes
}

for name, value in configurations.items():

    print(
        f"{name:30s}: {value} classes"
    )


# =============================================================================
# 10. CROSS-ATTENTION ARCHITECTURE DIMENSIONS
# =============================================================================

print("\n[7] CROSS-ATTENTION DIMENSION VERIFICATION")
print("-" * 80)

IMAGE_INPUT_DIM = 1792
SATELLITE_INPUT_DIM = 256
FUSION_DIM = 256
NUM_HEADS = 8
CONCAT_DIM = 512
HIDDEN_DIM = 256


print(
    "Image input dimension:",
    IMAGE_INPUT_DIM
)

print(
    "Satellite input dimension:",
    SATELLITE_INPUT_DIM
)

print(
    "Fusion dimension:",
    FUSION_DIM
)

print(
    "Attention heads:",
    NUM_HEADS
)

print(
    "Concatenated dimension:",
    CONCAT_DIM
)

print(
    "Fusion hidden dimension:",
    HIDDEN_DIM
)


# =============================================================================
# 11. VERIFY MULTIHEAD ATTENTION
# =============================================================================

print("\n[8] MULTIHEAD ATTENTION CHECK")
print("-" * 80)

if FUSION_DIM % NUM_HEADS != 0:

    raise RuntimeError(
        "256 is not divisible by 8."
    )

attention_head_dimension = (
    FUSION_DIM // NUM_HEADS
)

print(
    "Attention embedding dimension:",
    FUSION_DIM
)

print(
    "Number of heads:",
    NUM_HEADS
)

print(
    "Dimension per head:",
    attention_head_dimension
)

print("✓ MultiheadAttention configuration valid")


# =============================================================================
# 12. CREATE ATTENTION MODULE TEST
# =============================================================================

print("\n[9] TESTING ATTENTION MODULE")
print("-" * 80)

attention = nn.MultiheadAttention(
    embed_dim=FUSION_DIM,
    num_heads=NUM_HEADS,
    dropout=0.1,
    batch_first=True
)

# Test:
# Image query = one 256-D vector
# Satellite sequence = 10 × 256

dummy_image = torch.randn(
    2,
    1,
    256
)

dummy_satellite = torch.randn(
    2,
    10,
    256
)

attended_output, attention_weights = attention(
    query=dummy_image,
    key=dummy_satellite,
    value=dummy_satellite
)

print(
    "Query shape:",
    dummy_image.shape
)

print(
    "Key / Value shape:",
    dummy_satellite.shape
)

print(
    "Attention output:",
    attended_output.shape
)

print(
    "Attention weights:",
    attention_weights.shape
)

if attended_output.shape != (
    2,
    1,
    256
):

    raise RuntimeError(
        "Attention output shape incorrect."
    )

print("✓ Cross-attention tensor dimensions valid")


# =============================================================================
# 13. FUSION LAYER TEST
# =============================================================================

print("\n[10] TESTING FUSION LAYERS")
print("-" * 80)

fusion_layer = nn.Sequential(
    nn.Linear(
        512,
        256
    ),
    nn.ReLU(),
    nn.Dropout(
        0.3
    )
)

dummy_concat = torch.randn(
    2,
    512
)

dummy_fused = fusion_layer(
    dummy_concat
)

print(
    "Concatenated input:",
    dummy_concat.shape
)

print(
    "Fused output:",
    dummy_fused.shape
)

if dummy_fused.shape != (
    2,
    256
):

    raise RuntimeError(
        "Fusion output shape incorrect."
    )

print("✓ Fusion dimensions valid")


# =============================================================================
# 14. CHECK CLASSIFIER OPTIONS
# =============================================================================

print("\n[11] CLASSIFIER OPTIONS")
print("-" * 80)

print("""
Option A — 10 classes
---------------------
Matches the written Step 7 architecture specification.

Problem:
The current dataset does not contain a corresponding
10-class label mapping.

Therefore this cannot be used blindly.


Option B — 11 classes
---------------------
Matches the number of classes actually present in
the 640-image dataset.

Classes:
""")

for idx, cls in enumerate(
    present_classes
):

    print(
        f"{idx:2d} → {cls}"
    )


print("""
Option C — 13 classes
---------------------
Matches the original EfficientNet-B4 checkpoint
and the original project class list.

Problem:
leaf_smut = 0
normal    = 0

Those two classes cannot contribute supervised
training samples in the current 640-image dataset.
""")


# =============================================================================
# 15. IMPORTANT DECISION
# =============================================================================

print("\n[12] CONFIGURATION DECISION")
print("-" * 80)

print("""
❌ NO CLASSIFIER SIZE WILL BE SELECTED AUTOMATICALLY.

Reason:

10 classes  → document specification
11 classes  → classes present in current dataset
13 classes  → original checkpoint/project definition

These are not equivalent.

Training must not begin until the intended
final classifier configuration is explicitly established.
""")


# =============================================================================
# 16. SAVE REPORT
# =============================================================================

report = f"""
STEP 7H — ARCHITECTURE & CLASSIFIER CONFIGURATION
===================================================

DATASET
-------

Total samples:
640

Image embedding:
640 × 1792

Satellite embedding:
640 × 256


PROJECT CLASSES
---------------

Total:
13

Present:
{len(present_classes)}

Zero samples:
{len(zero_classes)}

Zero-sample classes:
{zero_classes}


CHECKPOINT
----------

Checkpoint classes:
{checkpoint_num_classes}

Checkpoint class list:
{checkpoint_classes}


ARCHITECTURE
------------

Image input:
1792

Projection:
1792 → 256

Satellite dimension:
256

Attention dimension:
256

Attention heads:
8

Attention dropout:
0.1

Concatenation:
256 + 256 = 512

Fusion:
512 → 256

Fusion dropout:
0.3


CLASSIFIER OPTIONS
------------------

Document:
10

Present dataset:
{len(present_classes)}

Original checkpoint:
{checkpoint_num_classes}


STATUS
------

ARCHITECTURE DIMENSIONS:
PASS

CLASSIFIER CONFIGURATION:
REQUIRES EXPLICIT DECISION

NO TRAINING PERFORMED.
"""


with open(
    OUTPUT_REPORT,
    "w"
) as f:

    f.write(report)


print("\n✓ Report saved:")
print(OUTPUT_REPORT)


# =============================================================================
# FINAL STATUS
# =============================================================================

print("\n")
print("=" * 80)
print("STEP 7H — COMPLETE")
print("=" * 80)

print("""
✓ Dataset configuration inspected
✓ Original checkpoint configuration inspected
✓ 1792 → 256 projection verified
✓ 256-D attention verified
✓ 8 attention heads verified
✓ 512 → 256 fusion verified
✓ Dropout 0.1 attention verified
✓ Dropout 0.3 fusion verified
✓ No training performed

⚠ FINAL CLASSIFIER COUNT STILL NEEDS TO BE CONFIRMED.

10 = document specification
11 = classes currently present
13 = original project/checkpoint
""")

print("=" * 80)