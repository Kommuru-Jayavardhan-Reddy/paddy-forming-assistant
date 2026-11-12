# ============================================================
# STEP 2B: IMAGE PREPROCESSING AND AUGMENTATION
# ============================================================

from pathlib import Path
from torchvision import transforms

# ImageNet statistics
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

# ------------------------------------------------------------
# TRAINING TRANSFORMATIONS
# ------------------------------------------------------------

train_transform = transforms.Compose([
    transforms.RandomResizedCrop(
        224,
        scale=(0.7, 1.0)
    ),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(30),
    transforms.ColorJitter(
        brightness=0.2,
        contrast=0.2,
        saturation=0.2
    ),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=IMAGENET_MEAN,
        std=IMAGENET_STD
    )
])

# ------------------------------------------------------------
# VALIDATION TRANSFORMATIONS
# ------------------------------------------------------------

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=IMAGENET_MEAN,
        std=IMAGENET_STD
    )
])

# ------------------------------------------------------------
# TEST TRANSFORMATIONS
# ------------------------------------------------------------

test_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=IMAGENET_MEAN,
        std=IMAGENET_STD
    )
])

# ------------------------------------------------------------
# DISPLAY CONFIGURATION
# ------------------------------------------------------------

print("=" * 60)
print("STEP 2B: PREPROCESSING & AUGMENTATION")
print("=" * 60)

print("Image size          : 224 x 224")
print("Normalization mean  :", IMAGENET_MEAN)
print("Normalization std   :", IMAGENET_STD)

print("\nTraining:")
print("  - RandomResizedCrop")
print("  - HorizontalFlip")
print("  - VerticalFlip")
print("  - Rotation ±30°")
print("  - ColorJitter")
print("  - ImageNet Normalization")

print("\nValidation:")
print("  - Resize 224 x 224")
print("  - ImageNet Normalization")

print("\nTest:")
print("  - Resize 224 x 224")
print("  - ImageNet Normalization")

print("=" * 60)
print("✅ Step 2B preprocessing setup completed")
print("=" * 60)

# ------------------------------------------------------------
# SAVE REPORT TO DRIVE
# ------------------------------------------------------------

RESULTS_DIR = Path(
    "/content/drive/MyDrive/final year project/results"
)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

report_path = RESULTS_DIR / "Step_2B_Preprocessing_Augmentation.txt"

with open(report_path, "w", encoding="utf-8") as f:
    f.write("STEP 2B: IMAGE PREPROCESSING AND AUGMENTATION\n")
    f.write("=" * 60 + "\n")
    f.write("Image size          : 224 x 224\n")
    f.write(f"Normalization mean  : {IMAGENET_MEAN}\n")
    f.write(f"Normalization std   : {IMAGENET_STD}\n\n")
    f.write("Training:\n")
    f.write("  - RandomResizedCrop\n")
    f.write("  - HorizontalFlip\n")
    f.write("  - VerticalFlip\n")
    f.write("  - Rotation ±30°\n")
    f.write("  - ColorJitter\n")
    f.write("  - ImageNet Normalization\n\n")
    f.write("Validation:\n")
    f.write("  - Resize 224 x 224\n")
    f.write("  - ImageNet Normalization\n\n")
    f.write("Test:\n")
    f.write("  - Resize 224 x 224\n")
    f.write("  - ImageNet Normalization\n")

print("\n📁 Report saved:")
print(report_path)