# ============================================================
# STEP 4A: EFFICIENTNET-B4 TRANSFER LEARNING SETUP
# ============================================================

import torch
import torch.nn as nn
from torchvision.models import efficientnet_b4, EfficientNet_B4_Weights

print("=" * 60)
print("STEP 4A: EFFICIENTNET-B4 SETUP")
print("=" * 60)

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Device :", device)

if torch.cuda.is_available():
    print("GPU    :", torch.cuda.get_device_name(0))

weights = EfficientNet_B4_Weights.DEFAULT

model = efficientnet_b4(
    weights=weights
)

for param in model.features.parameters():
    param.requires_grad = False

num_classes = len(classes)

model.classifier = nn.Sequential(
    nn.Linear(1792, 512),
    nn.ReLU(),
    nn.Dropout(0.4),
    nn.Linear(512, num_classes)
)

model = model.to(device)

trainable_params = sum(
    p.numel()
    for p in model.parameters()
    if p.requires_grad
)

total_params = sum(
    p.numel()
    for p in model.parameters()
)

print("\nNumber of classes :", num_classes)
print("Total parameters  :", f"{total_params:,}")
print("Trainable params  :", f"{trainable_params:,}")

print("\nClassifier:")
print(model.classifier)

print("\n" + "=" * 60)
print("EFFICIENTNET-B4 READY")
print("=" * 60)
