# ============================================================
# STEP 2C: DATASET AND DATALOADER SETUP
# ============================================================

import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from PIL import Image
from collections import Counter
from pathlib import Path

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

SPLIT_DIR = Path(
    "/content/drive/MyDrive/final year project/Dataset_Split"
)

# ------------------------------------------------------------
# CLASS NAMES
# ------------------------------------------------------------

classes = sorted([
    d.name for d in (SPLIT_DIR / "train").iterdir()
    if d.is_dir()
])

class_to_idx = {
    cls: i for i, cls in enumerate(classes)
}

print("Classes:")
for cls, idx in class_to_idx.items():
    print(f"{idx}: {cls}")

# ------------------------------------------------------------
# COLLECT IMAGE PATHS AND LABELS
# ------------------------------------------------------------

valid_extensions = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
}

def collect_images(split_name):
    split_dir = SPLIT_DIR / split_name

    image_paths = []
    labels = []

    for class_dir in sorted(split_dir.iterdir()):
        if class_dir.is_dir():

            for img in class_dir.iterdir():

                if (
                    img.is_file()
                    and img.suffix.lower() in valid_extensions
                ):
                    image_paths.append(str(img))
                    labels.append(class_dir.name)

    return image_paths, labels


X_train, y_train = collect_images("train")
X_val, y_val = collect_images("val")
X_test, y_test = collect_images("test")

print("\nImages loaded:")
print("Train      :", len(X_train))
print("Validation :", len(X_val))
print("Test       :", len(X_test))

# ------------------------------------------------------------
# CUSTOM DATASET
# ------------------------------------------------------------

class PaddyDataset(Dataset):

    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):

        image = Image.open(
            self.image_paths[idx]
        ).convert("RGB")

        label = class_to_idx[
            self.labels[idx]
        ]

        if self.transform:
            image = self.transform(image)

        return image, label


# ------------------------------------------------------------
# CHECK TRANSFORMS
# ------------------------------------------------------------

# If Step 2B was executed, these already exist.
# Otherwise, stop with a clear message.

if "train_transform" not in globals():
    raise RuntimeError(
        "train_transform not found. Run STEP 2B first."
    )

if "val_transform" not in globals():
    raise RuntimeError(
        "val_transform not found. Run STEP 2B first."
    )

if "test_transform" not in globals():
    raise RuntimeError(
        "test_transform not found. Run STEP 2B first."
    )

# ------------------------------------------------------------
# CREATE DATASETS
# ------------------------------------------------------------

train_dataset = PaddyDataset(
    X_train,
    y_train,
    train_transform
)

val_dataset = PaddyDataset(
    X_val,
    y_val,
    val_transform
)

test_dataset = PaddyDataset(
    X_test,
    y_test,
    test_transform
)

# ------------------------------------------------------------
# CLASS COUNTS
# ------------------------------------------------------------

class_counts = Counter(y_train)

# Sample weights for imbalance handling
sample_weights = [
    1.0 / class_counts[label]
    for label in y_train
]

sample_weights = torch.DoubleTensor(
    sample_weights
)

# ------------------------------------------------------------
# WEIGHTED RANDOM SAMPLER
# ------------------------------------------------------------

train_sampler = WeightedRandomSampler(
    weights=sample_weights,
    num_samples=len(sample_weights),
    replacement=True
)

# ------------------------------------------------------------
# DATALOADERS
# ------------------------------------------------------------

BATCH_SIZE = 32

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    sampler=train_sampler,
    num_workers=2,
    pin_memory=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=2,
    pin_memory=True
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=2,
    pin_memory=True
)

# ------------------------------------------------------------
# FINAL OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("STEP 2C: DATASET / DATALOADER SETUP")
print("=" * 60)

print("Train dataset :", len(train_dataset))
print("Validation    :", len(val_dataset))
print("Test dataset  :", len(test_dataset))
print("Batch size    :", BATCH_SIZE)

print("\nClass counts:")
for cls in classes:
    print(f"{cls:30s}: {class_counts[cls]}")

print("\nWeightedRandomSampler: ENABLED")

print("=" * 60)
print("✅ STEP 2C COMPLETED SUCCESSFULLY")
print("=" * 60)