# ============================================================
# STEP 4C: PHASE B - EFFICIENTNET-B4 FINE-TUNING
# COMPLETE DRIVE-SAVE VERSION
# ============================================================

import torch
import torch.nn as nn
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

CODE_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 2. CONFIGURATION
# ============================================================

EPOCHS = 5

print("=" * 60)
print("STEP 4C: PHASE B FINE-TUNING")
print("=" * 60)

print("Device       :", device)
print("Train samples:", len(train_loader.dataset))
print("Val samples  :", len(val_loader.dataset))
print("Classes      :", len(classes))

if torch.cuda.is_available():
    print("GPU          :", torch.cuda.get_device_name(0))

# ============================================================
# 3. LOAD PHASE A BEST MODEL
# ============================================================

PHASE_A_MODEL = (
    MODELS_DIR /
    "efficientnet_b4_phaseA_best.pth"
)

checkpoint = torch.load(
    PHASE_A_MODEL,
    map_location=device
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)

model = model.to(device)

print("\nPhase A model loaded:")
print(PHASE_A_MODEL)

# ============================================================
# 4. UNFREEZE ENTIRE BACKBONE
# ============================================================

for param in model.features.parameters():
    param.requires_grad = True

# ============================================================
# 5. DIFFERENTIAL LEARNING RATES
# ============================================================

optimizer = torch.optim.AdamW(
    [
        {
            "params": model.features[:-2].parameters(),
            "lr": 1e-5
        },
        {
            "params": model.features[-2:].parameters(),
            "lr": 1e-4
        },
        {
            "params": model.classifier.parameters(),
            "lr": 1e-4
        }
    ],
    weight_decay=1e-4
)

# ============================================================
# 6. LOSS
# ============================================================

criterion = nn.CrossEntropyLoss(
    label_smoothing=0.1
)

# ============================================================
# 7. SCHEDULER
# ============================================================

scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
    optimizer,
    T_max=EPOCHS
)

# ============================================================
# 8. PARAMETER CHECK
# ============================================================

trainable_params = sum(
    p.numel()
    for p in model.parameters()
    if p.requires_grad
)

total_params = sum(
    p.numel()
    for p in model.parameters()
)

print("\nModel Configuration")
print("-" * 60)
print("Total parameters     :", f"{total_params:,}")
print("Trainable parameters :", f"{trainable_params:,}")

print("\nLearning Rates:")
print("Early backbone       : 1e-5")
print("Last backbone blocks : 1e-4")
print("Classifier           : 1e-4")
print("Weight decay         : 1e-4")

print("\nBackbone Status : UNFROZEN")
print("Loss            : CrossEntropy + Label Smoothing 0.1")
print("Epochs          :", EPOCHS)

# ============================================================
# 9. BEST MODEL TRACKING
# ============================================================

best_val_acc = 0.0
best_epoch = 0
best_model_state = None

history = []

start_time = time.time()

# ============================================================
# 10. TRAINING LOOP
# ============================================================

for epoch in range(EPOCHS):

    print("\n" + "-" * 60)
    print(f"Epoch {epoch + 1}/{EPOCHS}")
    print("-" * 60)

    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # LEARNING RATE
    # --------------------------------------------------------

    current_lrs = [
        group["lr"]
        for group in optimizer.param_groups
    ]

    scheduler.step()

    # --------------------------------------------------------
    # BEST MODEL
    # --------------------------------------------------------

    if val_acc > best_val_acc:

        best_val_acc = val_acc
        best_epoch = epoch + 1

        best_model_state = {
            k: v.detach().cpu().clone()
            for k, v in model.state_dict().items()
        }

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    history.append({
        "epoch": epoch + 1,
        "train_loss": train_loss,
        "train_accuracy": train_acc,
        "val_loss": val_loss,
        "val_accuracy": val_acc,
        "early_backbone_lr": current_lrs[0],
        "last_backbone_lr": current_lrs[1],
        "classifier_lr": current_lrs[2]
    })

    # --------------------------------------------------------
    # PRINT
    # --------------------------------------------------------

    print(
        f"Train Loss : {train_loss:.4f}"
    )

    print(
        f"Train Acc  : {train_acc:.4f}"
    )

    print(
        f"Val Loss   : {val_loss:.4f}"
    )

    print(
        f"Val Acc    : {val_acc:.4f}"
    )

    print(
        f"Best Val   : {best_val_acc:.4f}"
    )

# ============================================================
# 11. RESTORE BEST MODEL
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
# 12. TRAINING TIME
# ============================================================

training_time = (
    time.time() - start_time
)

training_minutes = (
    training_time / 60
)

# ============================================================
# 13. SAVE BEST PHASE B MODEL
# ============================================================

BEST_MODEL_PATH = (
    MODELS_DIR /
    "efficientnet_b4_phaseB_best.pth"
)

torch.save(
    {
        "step": "4C",
        "phase": "Phase B",
        "architecture": "EfficientNet-B4",

        "model_state_dict":
            model.state_dict(),

        "classes": classes,

        "class_to_idx": {
            cls: idx
            for idx, cls in enumerate(classes)
        },

        "num_classes": len(classes),

        "best_epoch": best_epoch,

        "best_val_accuracy":
            best_val_acc,

        "epochs": EPOCHS,

        "learning_rates": {
            "early_backbone": 1e-5,
            "last_backbone_blocks": 1e-4,
            "classifier": 1e-4
        },

        "weight_decay": 1e-4,

        "optimizer": "AdamW",

        "loss": "CrossEntropyLoss",

        "label_smoothing": 0.1,

        "backbone_frozen": False,

        "input_size": [224, 224],

        "training_time_minutes":
            training_minutes,

        "created_at":
            str(datetime.now())
    },
    BEST_MODEL_PATH
)

# ============================================================
# 14. SAVE HISTORY CSV
# ============================================================

HISTORY_CSV = (
    RESULTS_DIR /
    "STEP_4C_EfficientNet_B4_PhaseB_History.csv"
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
            "early_backbone_lr",
            "last_backbone_lr",
            "classifier_lr"
        ]
    )

    writer.writeheader()
    writer.writerows(history)

# ============================================================
# 15. SAVE REPORT
# ============================================================

REPORT_TXT = (
    RESULTS_DIR /
    "STEP_4C_EfficientNet_B4_PhaseB_Report.txt"
)

with open(
    REPORT_TXT,
    "w"
) as f:

    f.write(
        "STEP 4C - EFFICIENTNET-B4 PHASE B FINE-TUNING\n"
    )

    f.write("=" * 70 + "\n\n")

    f.write(
        "Architecture      : EfficientNet-B4\n"
    )

    f.write(
        "Phase             : Phase B\n"
    )

    f.write(
        "Backbone          : Unfrozen\n"
    )

    f.write(
        f"Epochs            : {EPOCHS}\n"
    )

    f.write(
        "Early Backbone LR : 1e-5\n"
    )

    f.write(
        "Last Blocks LR    : 1e-4\n"
    )

    f.write(
        "Classifier LR     : 1e-4\n"
    )

    f.write(
        "Weight Decay      : 1e-4\n"
    )

    f.write(
        "Optimizer         : AdamW\n"
    )

    f.write(
        "Loss              : CrossEntropyLoss\n"
    )

    f.write(
        "Label Smoothing   : 0.1\n"
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
            f"Early LR: {row['early_backbone_lr']:.8f} | "
            f"Last LR: {row['last_backbone_lr']:.8f} | "
            f"Classifier LR: {row['classifier_lr']:.8f}\n"
        )

# ============================================================
# 16. SAVE METADATA JSON
# ============================================================

METADATA_JSON = (
    RESULTS_DIR /
    "STEP_4C_EfficientNet_B4_PhaseB_Metadata.json"
)

metadata = {

    "step": "4C",

    "phase": "Phase B",

    "architecture": "EfficientNet-B4",

    "backbone": "Unfrozen",

    "num_classes": len(classes),

    "classes": classes,

    "train_samples":
        len(train_loader.dataset),

    "validation_samples":
        len(val_loader.dataset),

    "epochs": EPOCHS,

    "learning_rates": {
        "early_backbone": 1e-5,
        "last_backbone_blocks": 1e-4,
        "classifier": 1e-4
    },

    "weight_decay": 1e-4,

    "optimizer": "AdamW",

    "loss": "CrossEntropyLoss",

    "label_smoothing": 0.1,

    "scheduler": "CosineAnnealingLR",

    "best_epoch": best_epoch,

    "best_validation_accuracy":
        best_val_acc,

    "training_time_minutes":
        training_minutes,

    "gpu": (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "CPU"
    ),

    "model_path":
        str(BEST_MODEL_PATH),

    "history_path":
        str(HISTORY_CSV),

    "report_path":
        str(REPORT_TXT),

    "created_at":
        str(datetime.now())
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
# 17. SAVE EXACT CODE
# ============================================================

CODE_FILE = (
    CODE_DIR /
    "STEP_4C_EfficientNet_B4_PhaseB_FineTuning_Training.py"
)

# IMPORTANT:
# The exact executed code should be saved manually after
# copying this cell into the file if required.

# ============================================================
# 18. FINAL OUTPUT
# ============================================================

print("\n" + "=" * 60)
print("🎉 STEP 4C PHASE B COMPLETED")
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

print("MODEL   :", BEST_MODEL_PATH)
print("HISTORY :", HISTORY_CSV)
print("REPORT  :", REPORT_TXT)
print("METADATA:", METADATA_JSON)

print("\n" + "=" * 60)
print("✅ PHASE B MODEL SAVED SAFELY TO GOOGLE DRIVE")
print("=" * 60)