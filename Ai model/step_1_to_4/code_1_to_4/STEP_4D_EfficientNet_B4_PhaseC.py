# ============================================================
# STEP 4D — PHASE C
# EFFICIENTNET-B4 EXTENDED FINE-TUNING — 30 EPOCHS
# ============================================================

import os
import time
import json
import pandas as pd
import torch
import torch.nn as nn

# ============================================================
# CONFIG
# ============================================================

EPOCHS = 30
LR = 1e-5
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1

# ============================================================
# DEVICE
# ============================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print("STEP 4D — PHASE C TRAINING")
print("=" * 70)
print("Device       :", device)

if torch.cuda.is_available():
    print("GPU          :", torch.cuda.get_device_name(0))

print("Epochs       :", EPOCHS)
print("Learning Rate:", LR)
print("Batch Size   :", train_loader.batch_size)
print("Train Images :", len(train_dataset))
print("Val Images   :", len(val_dataset))
print("=" * 70)

# ============================================================
# DRIVE SAVE PATHS
# ============================================================

SAVE_ROOT = "/content/drive/MyDrive/final year project"

MODEL_DIR = os.path.join(SAVE_ROOT, "models", "dl")
RESULT_DIR = os.path.join(SAVE_ROOT, "results")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

BEST_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "efficientnet_b4_phaseC_best.pth"
)

HISTORY_PATH = os.path.join(
    RESULT_DIR,
    "STEP_4D_EfficientNet_B4_PhaseC_History.csv"
)

METADATA_PATH = os.path.join(
    RESULT_DIR,
    "STEP_4D_EfficientNet_B4_PhaseC_Metadata.json"
)

# ============================================================
# LOSS
# ============================================================

criterion = nn.CrossEntropyLoss(
    label_smoothing=LABEL_SMOOTHING
)

# ============================================================
# OPTIMIZER
# ============================================================

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LR,
    weight_decay=WEIGHT_DECAY
)

# ============================================================
# COSINE ANNEALING
# ============================================================

scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
    optimizer,
    T_max=EPOCHS,
    eta_min=1e-7
)

# ============================================================
# MIXED PRECISION
# ============================================================

scaler = torch.amp.GradScaler("cuda")

# ============================================================
# TRAINING
# ============================================================

best_val_acc = 0.0
best_epoch = 0
history = []

total_start = time.time()

for epoch in range(1, EPOCHS + 1):

    epoch_start = time.time()

    # ========================================================
    # TRAIN
    # ========================================================

    model.train()

    train_loss = 0.0
    train_correct = 0
    train_total = 0

    for images, labels in train_loader:

        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        with torch.amp.autocast("cuda"):
            outputs = model(images)
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        train_loss += loss.item() * images.size(0)

        predicted = outputs.argmax(dim=1)

        train_total += labels.size(0)
        train_correct += (predicted == labels).sum().item()

    train_loss /= train_total
    train_acc = train_correct / train_total

    # ========================================================
    # VALIDATION
    # ========================================================

    model.eval()

    val_loss = 0.0
    val_correct = 0
    val_total = 0

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            with torch.amp.autocast("cuda"):
                outputs = model(images)
                loss = criterion(outputs, labels)

            val_loss += loss.item() * images.size(0)

            predicted = outputs.argmax(dim=1)

            val_total += labels.size(0)
            val_correct += (predicted == labels).sum().item()

    val_loss /= val_total
    val_acc = val_correct / val_total

    # ========================================================
    # SCHEDULER
    # ========================================================

    scheduler.step()

    current_lr = optimizer.param_groups[0]["lr"]

    epoch_time = (time.time() - epoch_start) / 60

    # ========================================================
    # HISTORY
    # ========================================================

    history.append({
        "epoch": epoch,
        "train_loss": train_loss,
        "train_accuracy": train_acc,
        "val_loss": val_loss,
        "val_accuracy": val_acc,
        "learning_rate": current_lr,
        "epoch_time_minutes": epoch_time
    })

    pd.DataFrame(history).to_csv(
        HISTORY_PATH,
        index=False
    )

    # ========================================================
    # SAVE BEST MODEL TO DRIVE
    # ========================================================

    if val_acc > best_val_acc:

        best_val_acc = val_acc
        best_epoch = epoch

        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "best_val_accuracy": best_val_acc,
                "classes": train_dataset.classes,
                "num_classes": len(train_dataset.classes),
                "model": "EfficientNet-B4",
                "phase": "Phase-C"
            },
            BEST_MODEL_PATH
        )

        marker = " ⭐ BEST"

    else:
        marker = ""

    # ========================================================
    # PRINT
    # ========================================================

    print(
        f"Epoch [{epoch:02d}/{EPOCHS}] | "
        f"Train Loss: {train_loss:.4f} | "
        f"Train Acc: {train_acc:.4f} | "
        f"Val Loss: {val_loss:.4f} | "
        f"Val Acc: {val_acc:.4f} | "
        f"LR: {current_lr:.2e} | "
        f"Time: {epoch_time:.2f} min"
        f"{marker}"
    )

# ============================================================
# METADATA
# ============================================================

total_time = (time.time() - total_start) / 60

metadata = {
    "model": "EfficientNet-B4",
    "phase": "Phase-C",
    "epochs": EPOCHS,
    "learning_rate": LR,
    "weight_decay": WEIGHT_DECAY,
    "label_smoothing": LABEL_SMOOTHING,
    "best_epoch": best_epoch,
    "best_validation_accuracy": best_val_acc,
    "training_time_minutes": total_time,
    "device": str(device),
    "gpu": torch.cuda.get_device_name(0)
        if torch.cuda.is_available() else "CPU",
    "classes": train_dataset.classes,
    "train_images": len(train_dataset),
    "validation_images": len(val_dataset)
}

with open(METADATA_PATH, "w") as f:
    json.dump(metadata, f, indent=4)

print("\n" + "=" * 70)
print("✅ STEP 4D — PHASE C COMPLETED")
print("=" * 70)
print("Best Epoch        :", best_epoch)
print(f"Best Val Accuracy : {best_val_acc:.4f}")
print(f"Total Time        : {total_time:.2f} minutes")

print("\nSaved to Drive:")
print("MODEL    :", BEST_MODEL_PATH)
print("HISTORY  :", HISTORY_PATH)
print("METADATA :", METADATA_PATH)
print("=" * 70)