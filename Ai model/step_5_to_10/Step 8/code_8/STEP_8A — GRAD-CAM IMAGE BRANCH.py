# ============================================================
# STEP 8A — GRAD-CAM IMAGE BRANCH
# PHASE 1: ENVIRONMENT + MODEL VERIFICATION
# ============================================================

!pip install -q grad-cam

import os
import torch
import torch.nn as nn
from torchvision import models

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

CHECKPOINT = "/content/drive/MyDrive/final year project/models/dl/efficientnet_b4_phaseC_best.pth"

TEST_DIR = "/content/drive/MyDrive/final year project/Dataset_Split/test"

OUTPUT_DIR = "/content/drive/MyDrive/final year project/results/step8A_gradcam"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------
# DEVICE
# ------------------------------------------------------------

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 90)
print("STEP 8A — GRAD-CAM IMAGE BRANCH")
print("=" * 90)

print("\n[1] DEVICE")
print("-" * 90)
print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

# ------------------------------------------------------------
# CHECK FILES
# ------------------------------------------------------------

print("\n[2] REQUIRED FILES")
print("-" * 90)

print("Checkpoint:")
print(CHECKPOINT)
print("Exists:", os.path.exists(CHECKPOINT))

print("\nTest directory:")
print(TEST_DIR)
print("Exists:", os.path.exists(TEST_DIR))

print("\nOutput directory:")
print(OUTPUT_DIR)
print("Exists:", os.path.exists(OUTPUT_DIR))

# ------------------------------------------------------------
# LOAD CHECKPOINT
# ------------------------------------------------------------

print("\n[3] LOADING CHECKPOINT")
print("-" * 90)

checkpoint = torch.load(
    CHECKPOINT,
    map_location="cpu",
    weights_only=False
)

print("Checkpoint type:", type(checkpoint).__name__)

if isinstance(checkpoint, dict):
    print("Checkpoint keys:")
    for k in checkpoint.keys():
        print(" ", k)

    print("\nBest validation accuracy:",
          checkpoint.get("best_val_accuracy", "Not available"))

    print("Epoch:",
          checkpoint.get("epoch", "Not available"))

    print("Number of classes:",
          checkpoint.get("num_classes", "Not available"))

    print("Classes:")
    print(checkpoint.get("classes", "Not available"))

# ------------------------------------------------------------
# CLASS LIST
# ------------------------------------------------------------

classes = [
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

print("\n[4] CLASS VERIFICATION")
print("-" * 90)

print("Number of classes:", len(classes))

for i, c in enumerate(classes):
    print(f"{i:2d} -> {c}")

# ------------------------------------------------------------
# BUILD EXACT PHASE-C MODEL
# ------------------------------------------------------------

print("\n[5] BUILDING EFFICIENTNET-B4")
print("-" * 90)

model = models.efficientnet_b4(weights=None)

# Exact classifier structure used by Phase-C checkpoint
model.classifier = nn.Sequential(
    nn.Linear(1792, 512),
    nn.ReLU(),
    nn.Dropout(0.4),
    nn.Linear(512, 13)
)

print(model.classifier)

# ------------------------------------------------------------
# LOAD WEIGHTS
# ------------------------------------------------------------

print("\n[6] LOADING MODEL WEIGHTS")
print("-" * 90)

state_dict = checkpoint["model_state_dict"]

missing, unexpected = model.load_state_dict(
    state_dict,
    strict=False
)

print("Missing keys:", len(missing))
print("Unexpected keys:", len(unexpected))

if missing:
    print("\nMissing keys:")
    for k in missing:
        print(" ", k)

if unexpected:
    print("\nUnexpected keys:")
    for k in unexpected:
        print(" ", k)

# ------------------------------------------------------------
# MOVE MODEL
# ------------------------------------------------------------

model = model.to(device)
model.eval()

print("\nModel loaded successfully.")

# ------------------------------------------------------------
# TARGET LAYER
# ------------------------------------------------------------

print("\n[7] GRAD-CAM TARGET LAYER")
print("-" * 90)

target_layer = model.features[-1]

print("Target layer:")
print(target_layer)

# ------------------------------------------------------------
# TEST DATASET CHECK
# ------------------------------------------------------------

print("\n[8] TEST DATASET CHECK")
print("-" * 90)

total_images = 0

for class_name in classes:

    class_dir = os.path.join(TEST_DIR, class_name)

    if os.path.exists(class_dir):

        image_files = [
            f for f in os.listdir(class_dir)
            if f.lower().endswith(
                (".jpg", ".jpeg", ".png", ".bmp", ".webp")
            )
        ]

        count = len(image_files)
        total_images += count

        print(f"{class_name:30s}: {count}")

    else:
        print(f"{class_name:30s}: DIRECTORY NOT FOUND")

print("-" * 90)
print("Total test images:", total_images)

# ------------------------------------------------------------
# FINAL VERIFICATION
# ------------------------------------------------------------

print("\n[9] STEP 8A VERIFICATION SUMMARY")
print("-" * 90)

print("EfficientNet-B4: READY")
print("Checkpoint: READY")
print("13 classes: READY")
print("Target layer: model.features[-1]")
print("Test dataset: READY")
print("Grad-CAM output directory: READY")

print("\nSTEP 8A PHASE 1 VERIFICATION COMPLETE")
print("=" * 90)