# ============================================================
# STEP 4F: GRAD-CAM - EFFICIENTNET-B4
# ============================================================

import torch
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from PIL import Image
from torchvision import transforms
from torchvision.datasets import ImageFolder

# ============================================================
# 1. SETUP
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

model = model.to(device)
model.eval()

TEST_ROOT = "/content/Paddy_Split/test"

CLASS_NAMES = [
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

# ============================================================
# 2. FIND LAST CONVOLUTIONAL LAYER
# ============================================================

target_layer = None

for module in reversed(list(model.modules())):

    if isinstance(module, torch.nn.Conv2d):
        target_layer = module
        break

print("Target Grad-CAM layer:")
print(target_layer)

# ============================================================
# 3. HOOKS
# ============================================================

activations = []
gradients = []

def forward_hook(module, input, output):
    activations.append(output)

def backward_hook(module, grad_input, grad_output):
    gradients.append(grad_output[0])

forward_handle = target_layer.register_forward_hook(
    forward_hook
)

backward_handle = target_layer.register_full_backward_hook(
    backward_hook
)

# ============================================================
# 4. SELECT TEST IMAGE
# ============================================================

dataset = ImageFolder(TEST_ROOT)

# Change this number if you want another image
IMAGE_INDEX = 0

image_path, true_label = dataset.samples[IMAGE_INDEX]

print("\nImage:")
print(image_path)

print(
    "True Class:",
    CLASS_NAMES[true_label]
)

# ============================================================
# 5. PREPROCESS IMAGE
# ============================================================

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])

original_image = Image.open(
    image_path
).convert("RGB")

input_tensor = transform(
    original_image
).unsqueeze(0).to(device)

# ============================================================
# 6. FORWARD PASS
# ============================================================

activations.clear()
gradients.clear()

output = model(input_tensor)

predicted_class = output.argmax(
    dim=1
).item()

confidence = torch.softmax(
    output,
    dim=1
)[0, predicted_class].item()

print(
    "\nPredicted Class:",
    CLASS_NAMES[predicted_class]
)

print(
    f"Confidence: {confidence * 100:.2f}%"
)

# ============================================================
# 7. BACKWARD PASS
# ============================================================

model.zero_grad()

score = output[
    0,
    predicted_class
]

score.backward()

# ============================================================
# 8. GRAD-CAM
# ============================================================

activation = activations[0]
gradient = gradients[0]

# Global average pooling of gradients
weights = gradient.mean(
    dim=(2, 3),
    keepdim=True
)

cam = (
    weights * activation
).sum(dim=1).squeeze()

cam = torch.relu(cam)

cam -= cam.min()

if cam.max() > 0:
    cam /= cam.max()

cam = cam.detach().cpu().numpy()

# Resize CAM to original image size
cam_image = Image.fromarray(
    np.uint8(cam * 255)
).resize(
    original_image.size
)

cam = np.array(cam_image) / 255.0

# ============================================================
# 9. CREATE OVERLAY
# ============================================================

original_np = np.array(
    original_image
).astype(np.float32) / 255.0

heatmap = plt.get_cmap("jet")(
    cam
)[:, :, :3]

overlay = (
    0.5 * original_np +
    0.5 * heatmap
)

overlay = np.clip(
    overlay,
    0,
    1
)

# ============================================================
# 10. DISPLAY
# ============================================================

plt.figure(figsize=(15, 5))

plt.subplot(1, 3, 1)

plt.imshow(original_image)

plt.title(
    f"Original\nTrue: {CLASS_NAMES[true_label]}"
)

plt.axis("off")

plt.subplot(1, 3, 2)

plt.imshow(cam, cmap="jet")

plt.title(
    "Grad-CAM Heatmap"
)

plt.axis("off")

plt.subplot(1, 3, 3)

plt.imshow(overlay)

plt.title(
    f"Grad-CAM Overlay\n"
    f"Pred: {CLASS_NAMES[predicted_class]}"
)

plt.axis("off")

plt.tight_layout()

plt.show()

# ============================================================
# 11. SAVE TO DRIVE
# ============================================================

RESULTS_DIR = Path(
    "/content/drive/MyDrive/final year project/results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

safe_name = Path(
    image_path
).stem

output_path = (
    RESULTS_DIR /
    f"STEP_4F_GradCAM_{safe_name}.png"
)

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight"
)

print("\n✅ Grad-CAM saved:")
print(output_path)

# ============================================================
# 12. REMOVE HOOKS
# ============================================================

forward_handle.remove()
backward_handle.remove()

print("✅ Grad-CAM completed")