
# ============================================================
# STEP 4E + 4F — TEST EVALUATION + TTA
# ============================================================

import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix
)
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json

# ============================================================
# PATHS
# ============================================================

DRIVE = '/content/drive/MyDrive/final year project'
RESULTS_DIR = f'{DRIVE}/results'

os.makedirs(RESULTS_DIR, exist_ok=True)

# ============================================================
# USE ALREADY LOADED PHASE-C MODEL
# ============================================================

model = model.to(device)
model.eval()

# ============================================================
# TEST DATASET
# ============================================================

classes = test_dataset.classes

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

# ============================================================
# PART A — STANDARD TEST EVALUATION
# ============================================================

std_preds = []
std_labels = []

with torch.no_grad():

    for images, labels in test_loader:

        images = images.to(device)

        outputs = model(images)

        preds = outputs.argmax(dim=1)

        std_preds.extend(preds.cpu().numpy())
        std_labels.extend(labels.cpu().numpy())

std_preds = np.array(std_preds)
std_labels = np.array(std_labels)

std_acc = accuracy_score(std_labels, std_preds)

std_f1w = f1_score(
    std_labels,
    std_preds,
    average='weighted',
    zero_division=0
)

std_f1m = f1_score(
    std_labels,
    std_preds,
    average='macro',
    zero_division=0
)

print(f"Standard Test Accuracy: {std_acc * 100:.2f}%")
print(f"Standard Weighted F1: {std_f1w:.4f}")
print(f"Standard Macro F1: {std_f1m:.4f}")

# ============================================================
# PART B — TTA
# ============================================================

tta_transforms = [

    transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            IMAGENET_MEAN,
            IMAGENET_STD
        )
    ]),

    transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=1.0),
        transforms.ToTensor(),
        transforms.Normalize(
            IMAGENET_MEAN,
            IMAGENET_STD
        )
    ]),

    transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomVerticalFlip(p=1.0),
        transforms.ToTensor(),
        transforms.Normalize(
            IMAGENET_MEAN,
            IMAGENET_STD
        )
    ]),

    transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomRotation((15, 15)),
        transforms.ToTensor(),
        transforms.Normalize(
            IMAGENET_MEAN,
            IMAGENET_STD
        )
    ]),

    transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomRotation((-15, -15)),
        transforms.ToTensor(),
        transforms.Normalize(
            IMAGENET_MEAN,
            IMAGENET_STD
        )
    ])
]

tta_preds = []
tta_labels = []

with torch.no_grad():

    for idx in range(len(test_dataset)):

        image_path, label = test_dataset.samples[idx]

        image = Image.open(
            image_path
        ).convert("RGB")

        probs = []

        for tf in tta_transforms:

            tensor = tf(image)
            tensor = tensor.unsqueeze(0).to(device)

            output = model(tensor)

            probability = torch.softmax(
                output,
                dim=1
            )

            probs.append(probability)

        mean_prob = torch.mean(
            torch.stack(probs),
            dim=0
        )

        prediction = mean_prob.argmax(
            dim=1
        ).item()

        tta_preds.append(prediction)
        tta_labels.append(int(label))

tta_preds = np.array(tta_preds)
tta_labels = np.array(tta_labels)

tta_acc = accuracy_score(
    tta_labels,
    tta_preds
)

tta_f1w = f1_score(
    tta_labels,
    tta_preds,
    average='weighted',
    zero_division=0
)

tta_f1m = f1_score(
    tta_labels,
    tta_preds,
    average='macro',
    zero_division=0
)

print("\nFINAL TTA RESULTS")
print(f"TTA Accuracy: {tta_acc * 100:.2f}%")
print(f"TTA Weighted F1: {tta_f1w:.4f}")
print(f"TTA Macro F1: {tta_f1m:.4f}")

# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    tta_labels,
    tta_preds
)

plt.figure(figsize=(16, 13))

sns.heatmap(
    cm,
    annot=True,
    fmt='d',
    xticklabels=classes,
    yticklabels=classes,
    cmap='Blues'
)

plt.title(
    f'EfficientNet-B4 + TTA\n'
    f'Test Accuracy: {tta_acc * 100:.2f}%'
)

plt.ylabel('True Label')
plt.xlabel('Predicted Label')

plt.xticks(rotation=45, ha='right')

plt.tight_layout()

plt.savefig(
    f'{RESULTS_DIR}/STEP_4F_confusion_matrix_TTA.png',
    dpi=150,
    bbox_inches='tight'
)

plt.close()

# ============================================================
# PER-CLASS ACCURACY
# ============================================================

per_cls = np.divide(
    cm.diagonal(),
    cm.sum(axis=1),
    out=np.zeros(len(classes)),
    where=cm.sum(axis=1) != 0
)

plt.figure(figsize=(16, 6))

bars = plt.bar(
    classes,
    per_cls * 100
)

plt.ylim(0, 115)

plt.ylabel('Accuracy (%)')

plt.title(
    'EfficientNet-B4 — Per-Class Accuracy with TTA'
)

plt.xticks(
    rotation=45,
    ha='right'
)

for bar, value in zip(bars, per_cls):

    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 1,
        f'{value * 100:.1f}%',
        ha='center',
        va='bottom',
        fontsize=8
    )

plt.tight_layout()

plt.savefig(
    f'{RESULTS_DIR}/STEP_4F_per_class_accuracy_TTA.png',
    dpi=150,
    bbox_inches='tight'
)

plt.close()

# ============================================================
# SAVE METRICS
# ============================================================

metrics = {
    'standard_test_acc':
        round(std_acc * 100, 2),

    'standard_weighted_f1':
        round(std_f1w, 4),

    'standard_macro_f1':
        round(std_f1m, 4),

    'tta_test_acc':
        round(tta_acc * 100, 2),

    'tta_weighted_f1':
        round(tta_f1w, 4),

    'tta_macro_f1':
        round(tta_f1m, 4)
}

with open(
    f'{RESULTS_DIR}/STEP_4F_final_metrics.json',
    'w'
) as f:

    json.dump(
        metrics,
        f,
        indent=4
    )

print("STEP 4E + 4F COMPLETE")
