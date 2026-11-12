# ============================================================
# STEP_8.1_SINGLE IMAGE GRAD-CAM TEST
# ============================================================
import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

# ------------------------------------------------------------
# SELECT ONE TEST IMAGE
# ------------------------------------------------------------

TEST_IMAGE = (
    "/content/drive/MyDrive/final year project/"
    "Dataset_Split/test/bacterial_leaf_blight/BLAST5_070.JPG"
)

OUTPUT_DIR = (
    "/content/drive/MyDrive/final year project/"
    "results/step8A_gradcam"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 90)
print("STEP 8A.1 — SINGLE IMAGE GRAD-CAM")
print("=" * 90)

print("\n[1] INPUT IMAGE")
print("-" * 90)
print("Path:", TEST_IMAGE)
print("Exists:", os.path.exists(TEST_IMAGE))

if not os.path.exists(TEST_IMAGE):
    raise FileNotFoundError(
        f"Test image not found:\n{TEST_IMAGE}"
    )

# ------------------------------------------------------------
# IMAGE PREPROCESSING
# ------------------------------------------------------------

transform = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# Read original image
original = Image.open(TEST_IMAGE).convert("RGB")

# RGB numpy image [0,1]
rgb_image = np.array(original.resize((380, 380))).astype(
    np.float32
) / 255.0

# Model input
input_tensor = transform(original).unsqueeze(0).to(device)

print("Original size:", original.size)
print("Model input:", tuple(input_tensor.shape))

# ------------------------------------------------------------
# MODEL PREDICTION
# ------------------------------------------------------------

print("\n[2] MODEL PREDICTION")
print("-" * 90)

model.eval()

with torch.no_grad():
    output = model(input_tensor)
    probabilities = torch.softmax(output, dim=1)

predicted_index = probabilities.argmax(dim=1).item()
confidence = probabilities[0, predicted_index].item()

predicted_class = classes[predicted_index]

print("Predicted class:", predicted_class)
print("Class index:", predicted_index)
print("Confidence:", f"{confidence * 100:.2f}%")

# ------------------------------------------------------------
# TOP-5 PREDICTIONS
# ------------------------------------------------------------

print("\n[3] TOP-5 PREDICTIONS")
print("-" * 90)

top5_prob, top5_idx = torch.topk(
    probabilities[0],
    k=5
)

for rank, (prob, idx) in enumerate(
    zip(top5_prob.cpu().numpy(), top5_idx.cpu().numpy()),
    start=1
):
    print(
        f"{rank}. "
        f"{classes[int(idx)]:30s} "
        f"{prob * 100:.2f}%"
    )

# ------------------------------------------------------------
# GRAD-CAM
# ------------------------------------------------------------

print("\n[4] GENERATING GRAD-CAM")
print("-" * 90)

target_layers = [model.features[-1]]

cam = GradCAM(
    model=model,
    target_layers=target_layers
)

targets = [
    ClassifierOutputTarget(predicted_index)
]

grayscale_cam = cam(
    input_tensor=input_tensor,
    targets=targets
)[0]

print("Grad-CAM shape:", grayscale_cam.shape)
print("Grad-CAM minimum:", float(grayscale_cam.min()))
print("Grad-CAM maximum:", float(grayscale_cam.max()))

# ------------------------------------------------------------
# CREATE OVERLAY
# ------------------------------------------------------------

visualization = show_cam_on_image(
    rgb_image,
    grayscale_cam,
    use_rgb=True
)

# ------------------------------------------------------------
# SAVE OUTPUT
# ------------------------------------------------------------

output_path = os.path.join(
    OUTPUT_DIR,
    "step8A_single_image_gradcam.png"
)

cv2.imwrite(
    output_path,
    cv2.cvtColor(visualization, cv2.COLOR_RGB2BGR)
)

print("\n[5] OUTPUT")
print("-" * 90)
print("Grad-CAM saved:")
print(output_path)
print("Exists:", os.path.exists(output_path))

# ------------------------------------------------------------
# DISPLAY
# ------------------------------------------------------------

plt.figure(figsize=(10, 5))

plt.imshow(visualization)
plt.title(
    f"Grad-CAM\n"
    f"Prediction: {predicted_class} "
    f"({confidence * 100:.2f}%)"
)
plt.axis("off")
plt.tight_layout()
plt.show()

# ------------------------------------------------------------
# FINAL STATUS
# ------------------------------------------------------------

print("\n" + "=" * 90)
print("STEP 8A — PHASE 2 COMPLETE")
print("=" * 90)
print("Prediction :", predicted_class)
print("Confidence :", f"{confidence * 100:.2f}%")
print("Grad-CAM   : Generated")
print("Output     :", output_path)
print("=" * 90)