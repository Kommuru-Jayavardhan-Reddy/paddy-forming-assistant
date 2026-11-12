# ============================================================
# STEP 4E — FINAL TEST EVALUATION
# BEST PHASE-C MODEL
# ============================================================

import os
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from torchvision import models
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)

# ============================================================
# PATH
# ============================================================

MODEL_PATH = "/content/drive/MyDrive/final year project/models/dl/efficientnet_b4_phaseC_best.pth"

RESULT_DIR = "/content/drive/MyDrive/final year project/results"

os.makedirs(RESULT_DIR, exist_ok=True)

# ============================================================
# LOAD CHECKPOINT
# ============================================================

checkpoint = torch.load(
    MODEL_PATH,
    map_location=device
)

state_dict = checkpoint["model_state_dict"]

# ============================================================
# RECREATE SAME MODEL ARCHITECTURE
# ============================================================

NUM_CLASSES = len(test_dataset.classes)

model = models.efficientnet_b4(weights=None)

in_features = model.classifier[1].in_features

model.classifier = nn.Sequential(
    nn.Linear(in_features, 512),
    nn.ReLU(),
    nn.Dropout(p=0.3),
    nn.Linear(512, NUM_CLASSES)
)

model.load_state_dict(state_dict)

model = model.to(device)
model.eval()

print("✅ Best Phase-C model loaded")
print("Best Epoch:", checkpoint["epoch"])
print("Best Validation Accuracy:",
      checkpoint["best_val_accuracy"])

# ============================================================
# TEST PREDICTIONS
# ============================================================

all_labels = []
all_predictions = []

with torch.no_grad():

    for images, labels in test_loader:

        images = images.to(device, non_blocking=True)

        outputs = model(images)

        predictions = outputs.argmax(dim=1)

        all_labels.extend(labels.numpy())
        all_predictions.extend(predictions.cpu().numpy())

# ============================================================
# METRICS
# ============================================================

accuracy = accuracy_score(
    all_labels,
    all_predictions
)

macro_precision = precision_score(
    all_labels,
    all_predictions,
    average="macro",
    zero_division=0
)

macro_recall = recall_score(
    all_labels,
    all_predictions,
    average="macro",
    zero_division=0
)

macro_f1 = f1_score(
    all_labels,
    all_predictions,
    average="macro",
    zero_division=0
)

weighted_f1 = f1_score(
    all_labels,
    all_predictions,
    average="weighted",
    zero_division=0
)

# ============================================================
# PRINT RESULTS
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST RESULTS")
print("=" * 70)

print(f"Test Accuracy       : {accuracy:.4f} ({accuracy*100:.2f}%)")
print(f"Macro Precision     : {macro_precision:.4f}")
print(f"Macro Recall        : {macro_recall:.4f}")
print(f"Macro F1            : {macro_f1:.4f}")
print(f"Weighted F1         : {weighted_f1:.4f}")

print("=" * 70)

# ============================================================
# CLASSIFICATION REPORT
# ============================================================

report = classification_report(
    all_labels,
    all_predictions,
    target_names=test_dataset.classes,
    digits=4,
    zero_division=0
)

print("\nCLASSIFICATION REPORT")
print("=" * 70)
print(report)

# Save report
REPORT_PATH = os.path.join(
    RESULT_DIR,
    "STEP_4E_Test_Classification_Report.txt"
)

with open(REPORT_PATH, "w") as f:

    f.write("STEP 4E — FINAL TEST EVALUATION\n")
    f.write("=" * 70 + "\n\n")

    f.write(f"Best Epoch: {checkpoint['epoch']}\n")
    f.write(
        f"Best Validation Accuracy: "
        f"{checkpoint['best_val_accuracy']:.4f}\n\n"
    )

    f.write(f"Test Accuracy: {accuracy:.4f}\n")
    f.write(f"Macro Precision: {macro_precision:.4f}\n")
    f.write(f"Macro Recall: {macro_recall:.4f}\n")
    f.write(f"Macro F1: {macro_f1:.4f}\n")
    f.write(f"Weighted F1: {weighted_f1:.4f}\n\n")

    f.write("CLASSIFICATION REPORT\n")
    f.write("=" * 70 + "\n")
    f.write(report)

# ============================================================
# SAVE METRICS CSV
# ============================================================

metrics_df = pd.DataFrame({
    "Metric": [
        "Accuracy",
        "Macro Precision",
        "Macro Recall",
        "Macro F1",
        "Weighted F1"
    ],
    "Score": [
        accuracy,
        macro_precision,
        macro_recall,
        macro_f1,
        weighted_f1
    ]
})

METRICS_PATH = os.path.join(
    RESULT_DIR,
    "STEP_4E_Test_Metrics.csv"
)

metrics_df.to_csv(
    METRICS_PATH,
    index=False
)

# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    all_labels,
    all_predictions
)

fig, ax = plt.subplots(figsize=(14, 12))

disp = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=test_dataset.classes
)

disp.plot(
    ax=ax,
    xticks_rotation=90,
    cmap="Blues",
    colorbar=True
)

plt.title(
    "EfficientNet-B4 Phase-C — Test Confusion Matrix"
)

plt.tight_layout()

CM_PATH = os.path.join(
    RESULT_DIR,
    "STEP_4E_Test_Confusion_Matrix.png"
)

plt.savefig(
    CM_PATH,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("✅ TEST EVALUATION COMPLETED")
print("=" * 70)

print("Classification Report:", REPORT_PATH)
print("Metrics CSV           :", METRICS_PATH)
print("Confusion Matrix      :", CM_PATH)
print("=" * 70)