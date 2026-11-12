# ============================================================
# STEP 2D: VISUALIZE + SAVE PREPROCESSING/AUGMENTATION
# ============================================================

import matplotlib.pyplot as plt
import torch
from PIL import Image
from pathlib import Path

# Paths
RESULTS_DIR = Path(
    "/content/drive/MyDrive/final year project/results"
)
CODE_DIR = Path(
    "/content/drive/MyDrive/final year project/code"
)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CODE_DIR.mkdir(parents=True, exist_ok=True)

# Get one original image
sample_path = X_train[0]
sample_label = y_train[0]

original_image = Image.open(sample_path).convert("RGB")

# Generate augmented images
augmented_images = [
    train_transform(original_image)
    for _ in range(4)
]

# Denormalize
def denormalize(img):
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)

    img = img * std + mean
    return torch.clamp(img, 0, 1)

# Create figure
plt.figure(figsize=(12, 8))

# Original
plt.subplot(2, 3, 1)
plt.imshow(original_image)
plt.title(f"Original\n{sample_label}")
plt.axis("off")

# Augmented
for i, img in enumerate(augmented_images):
    plt.subplot(2, 3, i + 2)

    img = denormalize(img)

    plt.imshow(img.permute(1, 2, 0))
    plt.title(f"Augmented {i + 1}")
    plt.axis("off")

plt.tight_layout()

# Save visualization
image_path = RESULTS_DIR / "Step_2D_Augmentation_Visualization.png"
plt.savefig(image_path, dpi=300, bbox_inches="tight")

plt.show()

print("✅ Step 2D visualization completed.")
print("📊 Visualization saved:")
print(image_path)

# Save code
code_path = CODE_DIR / "Step_2D_Visualization_Augmentation.py"

with open(code_path, "w", encoding="utf-8") as f:
    f.write(In[-1])

print("🐍 Code saved:")
print(code_path)