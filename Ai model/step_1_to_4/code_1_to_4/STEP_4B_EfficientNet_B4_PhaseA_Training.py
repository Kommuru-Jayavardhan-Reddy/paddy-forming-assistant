# ============================================================
# STEP 4B: EFFICIENTNET-B4 - PHASE A TRAINING
# COMPLETE DRIVE-SAVE VERSION
# ============================================================

import torch
import torch.nn as nn
import torch.optim as optim
import time
import json
import csv
from pathlib import Path
from datetime import datetime

# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(
    "/content/gdrive/MyDrive/final year project"
)

CODE_DIR = PROJECT_ROOT / "code"
RESULTS_DIR = PROJECT_ROOT / "results"
MODELS_DIR = PROJECT_ROOT / "models" / "dl"

CODE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MODELS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ============================================================
# 2. BASIC CHECKS
# ============================================================

print("=" * 60)
print("STEP 4B: PHASE A TRAINING")
print("=" * 60)

print("Device       :", device)
print("Train samples:", len(train_loader.dataset))
print("Val samples  :", len(val_loader.dataset))
print("Classes      :", len(classes))

if torch.cuda.is_available():
    print(
        "GPU          :",
        torch.cuda.get_device_name(0)
    )

# ============================================================
# 3. LOSS FUNCTION
# ============================================================

criterion = nn.CrossEntropyLoss(
    label_smoothing=0.1
)

# ============================================================
# 4. OPTIMIZER
# ONLY TRAINABLE PARAMETERS
# ============================================================

optimizer = optim.AdamW(
    filter(
        lambda p: p.requires_grad,
        model.parameters()
    ),
    lr=3e-4
)

# ============================================================
# 5. LEARNING RATE SCHEDULER
# ============================================================

scheduler = optim.lr_scheduler.CosineAnnealingLR(
    optimizer,
    T_max=5
)

# ============================================================
# 6. CONFIGURATION
# ============================================================

EPOCHS = 5

print("\nConfiguration:")
print("Epochs        :", EPOCHS)
print("Learning Rate :", 3e-4)
print("Optimizer     : AdamW")
print("Loss          : CrossEntropyLoss")
print("Label Smooth  : 0.1")
print("Backbone      : FROZEN")

# ============================================================
# 7. BEST MODEL TRACKING
# ============================================================

best_val_acc = 0.0
best_epoch = 0
best_model_state = None

history = []

start_time = time.time()

# ============================================================
# 8. TRAINING LOOP
# ============================================================

for epoch in range(EPOCHS):

    # ========================================================
    # TRAIN
    # ========================================================

    model.train()

    train_loss = 0.0
    train_correct = 0
    train_total = 0

    for images, labels in train_loader:

        images = images.to(
            device,
            non_blocking=True
        )

        labels = labels.to(
            device,
            non_blocking=True
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        outputs = model(images)

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()

        optimizer.step()

        train_loss += (
            loss.item() *
            images.size(0)
        )

        predicted = outputs.argmax(
            dim=1
        )

        train_correct += (
            predicted == labels
        ).sum().item()

        train_total += labels.size(0)

    train_loss /= train_total

    train_acc = (
        train_correct /
        train_total
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    model.eval()

    val_loss = 0.0
    val_correct = 0
    val_total = 0

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(
                device,
                non_blocking=True
            )

            labels = labels.to(
                device,
                non_blocking=True
            )

            outputs = model(images)

            loss = criterion(
                outputs,
                labels
            )

            val_loss += (
                loss.item() *
                images.size(0)
            )

            predicted = outputs.argmax(
                dim=1
            )

            val_correct += (
                predicted == labels
            ).sum().item()

            val_total += labels.size(0)

    val_loss /= val_total

    val_acc = (
        val_correct /
        val_total
    )

    # ========================================================
    # LEARNING RATE
    # ========================================================

    current_lr = optimizer.param_groups[0]["lr"]

    scheduler.step()

    # ========================================================
    # BEST MODEL
    # ========================================================

    if val_acc > best_val_acc:

        best_val_acc = val_acc
        best_epoch = epoch + 1

        best_model_state = {
            k: v.detach().cpu().clone()
            for k, v in model.state_dict().items()
        }

    # ========================================================
    # HISTORY
    # ========================================================

    history.append({
        "epoch": epoch + 1,
        "train_loss": train_loss,
        "train_accuracy": train_acc,
        "val_loss": val_loss,
        "val_accuracy": val_acc,
        "learning_rate": current_lr
    })

    # ========================================================
    # PRINT
    # ========================================================

    print(
        f"Epoch [{epoch+1}/{EPOCHS}] | "
        f"Train Loss: {train_loss:.4f} | "
        f"Train Acc: {train_acc:.4f} | "
        f"Val Loss: {val_loss:.4f} | "
        f"Val Acc: {val_acc:.4f} | "
        f"LR: {current_lr:.6f}"
    )

# ============================================================
# 9. RESTORE BEST MODEL
# ============================================================

if best_model_state is None:

    raise RuntimeError(
        "Best model state was not created."
    )

model.load_state_dict(
    best_model_state
)

model = model.to(device)

# ============================================================
# 10. TRAINING TIME
# ============================================================

training_time = (
    time.time() - start_time
)

training_minutes = (
    training_time / 60
)

# ============================================================
# 11. SAVE BEST MODEL
# ============================================================

BEST_MODEL_PATH = (
    MODELS_DIR /
    "efficientnet_b4_phaseA_best.pth"
)

torch.save(
    {
        "step": "4B",
        "phase": "Phase A",
        "architecture": "EfficientNet-B4",
        "model_state_dict": model.state_dict(),
        "classes": classes,
        "class_to_idx": {
            cls: idx
            for idx, cls in enumerate(classes)
        },
        "num_classes": len(classes),
        "best_epoch": best_epoch,
        "best_val_accuracy": best_val_acc,
        "epochs": EPOCHS,
        "learning_rate": 3e-4,
        "optimizer": "AdamW",
        "loss": "CrossEntropyLoss",
        "label_smoothing": 0.1,
        "backbone_frozen": True,
        "input_size": [224, 224],
        "training_time_minutes": training_minutes,
        "created_at": str(datetime.now())
    },
    BEST_MODEL_PATH
)

# ============================================================
# 12. SAVE HISTORY CSV
# ============================================================

HISTORY_CSV = (
    RESULTS_DIR /
    "STEP_4B_EfficientNet_B4_PhaseA_History.csv"
)

with open(
    HISTORY_CSV,
    "w",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "epoch",
            "train_loss",
            "train_accuracy",
            "val_loss",
            "val_accuracy",
            "learning_rate"
        ]
    )

    writer.writeheader()
    writer.writerows(history)

# ============================================================
# 13. SAVE REPORT
# ============================================================

REPORT_TXT = (
    RESULTS_DIR /
    "STEP_4B_EfficientNet_B4_PhaseA_Report.txt"
)

with open(
    REPORT_TXT,
    "w"
) as f:

    f.write(
        "STEP 4B - EFFICIENTNET-B4 PHASE A TRAINING\n"
    )

    f.write("=" * 70 + "\n\n")

    f.write(
        f"Architecture      : EfficientNet-B4\n"
    )

    f.write(
        f"Phase             : Phase A\n"
    )

    f.write(
        f"Backbone          : Frozen\n"
    )

    f.write(
        f"Epochs            : {EPOCHS}\n"
    )

    f.write(
        f"Learning Rate     : 3e-4\n"
    )

    f.write(
        f"Optimizer         : AdamW\n"
    )

    f.write(
        f"Loss              : CrossEntropyLoss\n"
    )

    f.write(
        f"Label Smoothing   : 0.1\n"
    )

    f.write(
        f"Train Samples     : {len(train_loader.dataset)}\n"
    )

    f.write(
        f"Validation Samples: {len(val_loader.dataset)}\n"
    )

    f.write(
        f"Best Epoch        : {best_epoch}\n"
    )

    f.write(
        f"Best Val Accuracy : {best_val_acc:.6f}\n"
    )

    f.write(
        f"Training Time     : {training_minutes:.2f} minutes\n"
    )

    f.write(
        f"GPU               : "
        f"{torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}\n"
    )

    f.write(
        f"Completed At      : {datetime.now()}\n\n"
    )

    f.write("=" * 70 + "\n")
    f.write("EPOCH HISTORY\n")
    f.write("=" * 70 + "\n\n")

    for row in history:

        f.write(
            f"Epoch {row['epoch']} | "
            f"Train Loss: {row['train_loss']:.4f} | "
            f"Train Acc: {row['train_accuracy']:.4f} | "
            f"Val Loss: {row['val_loss']:.4f} | "
            f"Val Acc: {row['val_accuracy']:.4f} | "
            f"LR: {row['learning_rate']:.6f}\n"
        )

# ============================================================
# 14. SAVE METADATA JSON
# ============================================================

METADATA_JSON = (
    RESULTS_DIR /
    "STEP_4B_EfficientNet_B4_PhaseA_Metadata.json"
)

metadata = {
    "step": "4B",
    "phase": "Phase A",
    "architecture": "EfficientNet-B4",
    "backbone": "Frozen",
    "num_classes": len(classes),
    "classes": classes,
    "train_samples": len(train_loader.dataset),
    "validation_samples": len(val_loader.dataset),
    "epochs": EPOCHS,
    "learning_rate": 3e-4,
    "optimizer": "AdamW",
    "loss": "CrossEntropyLoss",
    "label_smoothing": 0.1,
    "scheduler": "CosineAnnealingLR",
    "scheduler_T_max": 5,
    "best_epoch": best_epoch,
    "best_validation_accuracy": best_val_acc,
    "training_time_minutes": training_minutes,
    "gpu": (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "CPU"
    ),
    "model_path": str(BEST_MODEL_PATH),
    "history_path": str(HISTORY_CSV),
    "report_path": str(REPORT_TXT),
    "created_at": str(datetime.now())
}

with open(
    METADATA_JSON,
    "w"
) as f:

    json.dump(
        metadata,
        f,
        indent=4
    )

# ============================================================
# 15. FINAL OUTPUT
# ============================================================

print("\n" + "=" * 60)
print("🎉 STEP 4B PHASE A COMPLETED")
print("=" * 60)

print(
    f"Training Time : {training_minutes:.2f} minutes"
)

print(
    f"Best Epoch    : {best_epoch}"
)

print(
    f"Best Val Acc  : {best_val_acc:.4f}"
)

print("\nDRIVE FILES SAVED:")
print("-" * 60)

print(
    "MODEL   :",
    BEST_MODEL_PATH
)

print(
    "HISTORY :",
    HISTORY_CSV
)

print(
    "REPORT  :",
    REPORT_TXT
)

print(
    "METADATA:",
    METADATA_JSON
)

print("\n" + "=" * 60)
print("✅ PHASE A MODEL SAVED SAFELY TO GOOGLE DRIVE")
print("=" * 60)
