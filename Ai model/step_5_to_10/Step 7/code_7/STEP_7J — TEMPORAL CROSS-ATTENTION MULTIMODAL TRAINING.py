# ================================================================================
# STEP_7J — TEMPORAL CROSS-ATTENTION MULTIMODAL TRAINING
# ================================================================================
#
# CORRECTED VERSION
#
# IMPORTANT:
#   satellite_embedding_index          = FIELD / satellite sequence index
#   paired_satellite_embedding_index   = 640-image row index
#
# Therefore:
#   DO NOT compare these two columns.
#   DO NOT use paired_satellite_embedding_index for temporal mapping.
#
# Satellite sequence:
#   FIELD_01 -> index 0
#   FIELD_02 -> index 1
#   ...
#   FIELD_58 -> index 57
#
# Final temporal sequence:
#   640 images x 10 timesteps x 3 features
#
# BiLSTM:
#   (B,10,3) -> (B,10,256)
#
# Cross Attention:
#   Image query:    (B,1,256)
#   Satellite K/V:  (B,10,256)
#   Attention:      (B,1,10)
#
# ================================================================================


# ================================================================================
# 0. IMPORTS
# ================================================================================

import os
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from collections import Counter

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report
)

from sklearn.utils.class_weight import compute_class_weight

from google.colab import drive


# ================================================================================
# 1. MOUNT GOOGLE DRIVE
# ================================================================================

print("=" * 80)
print("STEP 7L — TEMPORAL CROSS-ATTENTION MULTIMODAL TRAINING")
print("=" * 80)

print("\n[1] MOUNTING GOOGLE DRIVE")
print("-" * 80)

drive.mount("/content/drive", force_remount=False)

print("✓ Google Drive connected")


# ================================================================================
# 2. RANDOM SEED
# ================================================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

print("\n[2] RANDOM SEED")
print("-" * 80)
print("Seed:", SEED)


# ================================================================================
# 3. DEVICE
# ================================================================================

print("\n[3] DEVICE")
print("-" * 80)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    print("WARNING: CUDA not available")


# ================================================================================
# 4. PATHS
# ================================================================================

BASE_DIR = "/content/drive/MyDrive/final year project/Real_world_test"

STEP5_DIR = os.path.join(BASE_DIR, "Step 5")
STEP7_DIR = os.path.join(BASE_DIR, "Step 7")

DATASET_PATH = os.path.join(
    STEP7_DIR,
    "step7I_final_11class_multimodal_dataset.csv"
)

IMAGE_EMBEDDING_PATH = os.path.join(
    STEP7_DIR,
    "step7_FINAL_image_embeddings_1792.npy"
)

TRAIN_INDEX_PATH = os.path.join(
    STEP7_DIR,
    "step7I_train_indices.npy"
)

VAL_INDEX_PATH = os.path.join(
    STEP7_DIR,
    "step7I_val_indices.npy"
)

# IMPORTANT:
# Temporal satellite sequence is in STEP 5, not STEP 6.
SATELLITE_SEQUENCE_PATH = os.path.join(
    STEP5_DIR,
    "bilstm_sequences.npy"
)

OUTPUT_DIR = os.path.join(
    STEP7_DIR,
    "Step7L_Temporal_CrossAttention"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


print("\n[4] REQUIRED FILES")
print("-" * 80)

required_files = {
    "Dataset": DATASET_PATH,
    "Image embeddings": IMAGE_EMBEDDING_PATH,
    "Train indices": TRAIN_INDEX_PATH,
    "Validation indices": VAL_INDEX_PATH,
    "Satellite temporal sequences": SATELLITE_SEQUENCE_PATH,
}

all_exist = True

for name, path in required_files.items():

    exists = os.path.exists(path)

    print(
        f"{'✓' if exists else '✗'} {name}:"
    )
    print("  ", path)

    if not exists:
        all_exist = False

if not all_exist:
    raise FileNotFoundError(
        "\n❌ One or more required files are missing."
    )

print("\n✓ All required files found")


# ================================================================================
# 5. LOAD DATA
# ================================================================================

print("\n[5] LOADING DATA")
print("-" * 80)

df = pd.read_csv(DATASET_PATH)

image_embeddings = np.load(
    IMAGE_EMBEDDING_PATH
).astype(np.float32)

train_indices = np.load(
    TRAIN_INDEX_PATH
).astype(np.int64)

val_indices = np.load(
    VAL_INDEX_PATH
).astype(np.int64)

satellite_sequences = np.load(
    SATELLITE_SEQUENCE_PATH
).astype(np.float32)


print("Dataset shape:", df.shape)
print("Image embeddings shape:", image_embeddings.shape)
print("Train indices shape:", train_indices.shape)
print("Validation indices shape:", val_indices.shape)
print("Satellite sequences shape:", satellite_sequences.shape)


# ================================================================================
# 6. BASIC SHAPE VALIDATION
# ================================================================================

print("\n[6] BASIC VALIDATION")
print("-" * 80)

assert len(df) == 640, \
    f"Expected 640 dataset records, got {len(df)}"

assert image_embeddings.shape == (640, 1792), \
    f"Unexpected image embedding shape: {image_embeddings.shape}"

assert satellite_sequences.shape == (58, 10, 3), \
    f"Unexpected satellite sequence shape: {satellite_sequences.shape}"

assert len(train_indices) == 512, \
    f"Expected 512 train samples, got {len(train_indices)}"

assert len(val_indices) == 128, \
    f"Expected 128 validation samples, got {len(val_indices)}"

print("✓ Dataset = 640")
print("✓ Image embeddings = (640,1792)")
print("✓ Satellite sequences = (58,10,3)")
print("✓ Train = 512")
print("✓ Validation = 128")


# ================================================================================
# 7. CHECK NAN / INF
# ================================================================================

print("\n[7] NUMERICAL VALIDATION")
print("-" * 80)

print(
    "Image NaN:",
    np.isnan(image_embeddings).sum()
)

print(
    "Image Inf:",
    np.isinf(image_embeddings).sum()
)

print(
    "Satellite NaN:",
    np.isnan(satellite_sequences).sum()
)

print(
    "Satellite Inf:",
    np.isinf(satellite_sequences).sum()
)

assert not np.isnan(image_embeddings).any()
assert not np.isinf(image_embeddings).any()

assert not np.isnan(satellite_sequences).any()
assert not np.isinf(satellite_sequences).any()

print("✓ No NaN values")
print("✓ No Inf values")


# ================================================================================
# 8. VERIFY TRAIN / VALIDATION SPLIT
# ================================================================================

print("\n[8] TRAIN / VALIDATION SPLIT")
print("-" * 80)

train_set = set(train_indices.tolist())
val_set = set(val_indices.tolist())

overlap = train_set.intersection(val_set)

print("Train samples:", len(train_set))
print("Validation samples:", len(val_set))
print("Overlap:", len(overlap))

assert len(overlap) == 0, \
    "❌ Train/validation overlap detected"

print("✓ No train/validation overlap")


# ================================================================================
# 9. VERIFY 11-CLASS LABELS
# ================================================================================

print("\n[9] 11-CLASS LABEL VERIFICATION")
print("-" * 80)

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
    "sheath_blight",
    "tungro"
]

NUM_CLASSES = 11

assert "label_11class" in df.columns, \
    "❌ label_11class column missing"

labels = df["label_11class"].astype(int).to_numpy()

unique_labels = sorted(np.unique(labels).tolist())

print("Unique labels:", unique_labels)

assert unique_labels == list(range(NUM_CLASSES)), \
    f"Unexpected labels: {unique_labels}"

print("\nClass distribution:")

for i, name in enumerate(CLASS_NAMES):

    count = int((labels == i).sum())

    print(
        f"{i:2d} | {name:<30} | {count}"
    )

print("\n✓ All 11 classes verified")


# ================================================================================
# 10. CORRECT SATELLITE TEMPORAL MAPPING
# ================================================================================

print("\n[10] CORRECT SATELLITE TEMPORAL MAPPING")
print("-" * 80)

print("""
IMPORTANT:

satellite_embedding_index
    = satellite FIELD index

paired_satellite_embedding_index
    = 640-image row index

Therefore paired_satellite_embedding_index
is NOT used for temporal satellite mapping.
""")

assert "satellite_embedding_index" in df.columns

assert "nearest_satellite_field" in df.columns

satellite_indices = (
    df["satellite_embedding_index"]
    .astype(int)
    .to_numpy()
)

print(
    "Satellite index min:",
    satellite_indices.min()
)

print(
    "Satellite index max:",
    satellite_indices.max()
)

print(
    "Unique satellite indices:",
    len(np.unique(satellite_indices))
)

# Valid index range
assert satellite_indices.min() >= 0

assert satellite_indices.max() < len(
    satellite_sequences
), (
    f"Satellite index {satellite_indices.max()} "
    f"is outside sequence range 0-{len(satellite_sequences)-1}"
)

print("✓ Satellite index range valid")


# ================================================================================
# 11. FIELD NAME VALIDATION
# ================================================================================

print("\n[11] FIELD NAME VALIDATION")
print("-" * 80)

field_mismatch_count = 0

mismatch_examples = []

for i in range(len(df)):

    seq_idx = int(
        satellite_indices[i]
    )

    expected_field = (
        f"FIELD_{seq_idx + 1:02d}"
    )

    actual_field = str(
        df.iloc[i]["nearest_satellite_field"]
    ).strip()

    if expected_field != actual_field:

        field_mismatch_count += 1

        if len(mismatch_examples) < 10:

            mismatch_examples.append(
                (
                    i,
                    seq_idx,
                    expected_field,
                    actual_field
                )
            )


print(
    "Field mapping mismatches:",
    field_mismatch_count
)

if field_mismatch_count > 0:

    print("\nFirst mismatches:")

    for item in mismatch_examples:

        print(
            f"Row {item[0]} | "
            f"index={item[1]} | "
            f"expected={item[2]} | "
            f"actual={item[3]}"
        )

    raise ValueError(
        "❌ satellite_embedding_index does not match "
        "nearest_satellite_field"
    )

print("✓ satellite_embedding_index correctly maps to nearest_satellite_field")


# ================================================================================
# 12. CREATE IMAGE → TEMPORAL SATELLITE SEQUENCES
# ================================================================================

print("\n[12] BUILDING IMAGE → TEMPORAL SATELLITE SEQUENCES")
print("-" * 80)

image_satellite_sequences = (
    satellite_sequences[
        satellite_indices
    ].copy()
)

print(
    "Image temporal satellite shape:",
    image_satellite_sequences.shape
)

assert image_satellite_sequences.shape == (
    640,
    10,
    3
)

print("""
✓ 640 images mapped
✓ 10 satellite timesteps per image
✓ 3 satellite features per timestep
""")

print("Features:")
print("  1. NDVI")
print("  2. NDRE")
print("  3. GNDVI")


# ================================================================================
# 13. VERIFY A FEW MAPPINGS
# ================================================================================

print("\n[13] SAMPLE SATELLITE MAPPING")
print("-" * 80)

for i in range(min(10, len(df))):

    print(
        f"Row {i:03d} | "
        f"Field={df.iloc[i]['nearest_satellite_field']} | "
        f"SatelliteIndex={satellite_indices[i]} | "
        f"SequenceShape={image_satellite_sequences[i].shape}"
    )


# ================================================================================
# 14. NOTE ABOUT BiLSTM
# ================================================================================

print("\n[14] BiLSTM CHECK")
print("-" * 80)

print("""
No original Step 6 BiLSTM checkpoint was found.

Therefore Step 7L will TRAIN a BiLSTM jointly
with the temporal cross-attention model.

Input:
    10 timesteps × 3 features

BiLSTM:
    input_size  = 3
    hidden_size = 128
    bidirectional = True

Output:
    10 timesteps × 256

This preserves the temporal satellite information.
""")


# ================================================================================
# 15. PYTORCH DATASET
# ================================================================================

class PaddyMultimodalDataset(Dataset):

    def __init__(
        self,
        image_embeddings,
        satellite_sequences,
        labels,
        indices
    ):

        self.image_embeddings = torch.tensor(
            image_embeddings[indices],
            dtype=torch.float32
        )

        self.satellite_sequences = torch.tensor(
            satellite_sequences[indices],
            dtype=torch.float32
        )

        self.labels = torch.tensor(
            labels[indices],
            dtype=torch.long
        )

    def __len__(self):

        return len(self.labels)

    def __getitem__(self, idx):

        return (
            self.image_embeddings[idx],
            self.satellite_sequences[idx],
            self.labels[idx]
        )


# ================================================================================
# 16. CREATE DATASETS
# ================================================================================

print("\n[15] CREATING PYTORCH DATASETS")
print("-" * 80)

train_dataset = PaddyMultimodalDataset(
    image_embeddings,
    image_satellite_sequences,
    labels,
    train_indices
)

val_dataset = PaddyMultimodalDataset(
    image_embeddings,
    image_satellite_sequences,
    labels,
    val_indices
)

print("Train dataset:", len(train_dataset))
print("Validation dataset:", len(val_dataset))


# ================================================================================
# 17. DATA LOADERS
# ================================================================================

BATCH_SIZE = 32

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
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

print("Batch size:", BATCH_SIZE)


# ================================================================================
# 18. MODEL
# ================================================================================

class TemporalCrossAttentionModel(nn.Module):

    def __init__(
        self,
        image_dim=1792,
        satellite_input_dim=3,
        lstm_hidden=128,
        projection_dim=256,
        num_heads=8,
        num_classes=11
    ):

        super().__init__()

        # ------------------------------------------------
        # IMAGE BRANCH
        # ------------------------------------------------

        self.image_projection = nn.Sequential(

            nn.Linear(
                image_dim,
                projection_dim
            ),

            nn.LayerNorm(
                projection_dim
            ),

            nn.ReLU(),

            nn.Dropout(0.10)
        )


        # ------------------------------------------------
        # SATELLITE TEMPORAL BRANCH
        # ------------------------------------------------

        self.satellite_lstm = nn.LSTM(

            input_size=satellite_input_dim,

            hidden_size=lstm_hidden,

            num_layers=2,

            batch_first=True,

            dropout=0.20,

            bidirectional=True
        )


        # BiLSTM output:
        # 128 forward + 128 backward = 256

        self.satellite_projection = nn.Sequential(

            nn.Linear(
                lstm_hidden * 2,
                projection_dim
            ),

            nn.LayerNorm(
                projection_dim
            ),

            nn.ReLU()
        )


        # ------------------------------------------------
        # TEMPORAL CROSS ATTENTION
        # ------------------------------------------------

        self.cross_attention = nn.MultiheadAttention(

            embed_dim=projection_dim,

            num_heads=num_heads,

            dropout=0.10,

            batch_first=True
        )


        # ------------------------------------------------
        # FUSION
        # ------------------------------------------------

        self.fusion = nn.Sequential(

            nn.Linear(
                projection_dim * 2,
                256
            ),

            nn.ReLU(),

            nn.Dropout(0.30)
        )


        # ------------------------------------------------
        # CLASSIFIER
        # ------------------------------------------------

        self.classifier = nn.Linear(
            256,
            num_classes
        )


    def forward(
        self,
        image_embedding,
        satellite_sequence,
        return_attention=False
    ):

        # =================================================
        # IMAGE
        # =================================================

        image_features = self.image_projection(
            image_embedding
        )

        # Shape:
        # (B,1792) -> (B,256)


        # =================================================
        # SATELLITE BiLSTM
        # =================================================

        satellite_lstm_output, _ = (
            self.satellite_lstm(
                satellite_sequence
            )
        )

        # Shape:
        # (B,10,3)
        # ->
        # (B,10,256)


        satellite_features = self.satellite_projection(
            satellite_lstm_output
        )

        # Shape:
        # (B,10,256)


        # =================================================
        # IMAGE AS QUERY
        # =================================================

        query = image_features.unsqueeze(1)

        # Shape:
        # (B,1,256)


        # =================================================
        # SATELLITE AS KEY / VALUE
        # =================================================

        key = satellite_features

        value = satellite_features

        # Shape:
        # (B,10,256)


        # =================================================
        # CROSS ATTENTION
        # =================================================

        attended_features, attention_weights = (
            self.cross_attention(
                query=query,
                key=key,
                value=value
            )
        )

        # attended_features:
        # (B,1,256)

        # attention_weights:
        # (B,1,10)


        attended_features = (
            attended_features.squeeze(1)
        )

        # Shape:
        # (B,256)


        # =================================================
        # FUSION
        # =================================================

        fused = torch.cat(
            [
                image_features,
                attended_features
            ],
            dim=1
        )

        # Shape:
        # (B,512)


        fused = self.fusion(fused)

        # Shape:
        # (B,256)


        # =================================================
        # CLASSIFIER
        # =================================================

        logits = self.classifier(fused)

        # Shape:
        # (B,11)


        if return_attention:

            return (
                logits,
                attention_weights
            )

        return logits


# ================================================================================
# 19. INITIALIZE MODEL
# ================================================================================

print("\n[16] INITIALIZING MODEL")
print("-" * 80)

model = TemporalCrossAttentionModel(
    image_dim=1792,
    satellite_input_dim=3,
    lstm_hidden=128,
    projection_dim=256,
    num_heads=8,
    num_classes=11
).to(device)

print(model)


# ================================================================================
# 20. PARAMETER COUNT
# ================================================================================

total_params = sum(
    p.numel()
    for p in model.parameters()
)

trainable_params = sum(
    p.numel()
    for p in model.parameters()
    if p.requires_grad
)

print("\nTotal parameters:", total_params)
print("Trainable parameters:", trainable_params)


# ================================================================================
# 21. FORWARD PASS TEST
# ================================================================================

print("\n[17] FORWARD PASS TEST")
print("-" * 80)

sample_images, sample_satellite, sample_labels = next(
    iter(train_loader)
)

sample_images = sample_images.to(device)
sample_satellite = sample_satellite.to(device)

with torch.no_grad():

    sample_logits, sample_attention = model(
        sample_images[:2],
        sample_satellite[:2],
        return_attention=True
    )

print(
    "Image input:",
    sample_images[:2].shape
)

print(
    "Satellite input:",
    sample_satellite[:2].shape
)

print(
    "Logits:",
    sample_logits.shape
)

print(
    "Attention:",
    sample_attention.shape
)

assert sample_logits.shape == (2, 11)

assert sample_attention.shape == (2, 1, 10)

print("\n✓ Forward pass successful")

print("""
IMPORTANT:
Attention shape = [2, 1, 10]

This means:
2 samples
1 image query
10 satellite timesteps

This is the intended TEMPORAL cross-attention.
""")


# ================================================================================
# 22. CLASS-BALANCED LOSS
# ================================================================================

print("\n[18] CLASS-BALANCED LOSS")
print("-" * 80)

train_labels = labels[train_indices]

class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.arange(NUM_CLASSES),
    y=train_labels
)

class_weights = torch.tensor(
    class_weights,
    dtype=torch.float32
).to(device)

print("Class weights:")

for i, weight in enumerate(class_weights):

    print(
        f"{i:2d} | "
        f"{CLASS_NAMES[i]:<30} | "
        f"{weight.item():.4f}"
    )


# ================================================================================
# 23. LOSS FUNCTION
# ================================================================================

criterion = nn.CrossEntropyLoss(
    weight=class_weights,
    label_smoothing=0.05
)


# ================================================================================
# 24. OPTIMIZER
# ================================================================================

LEARNING_RATE = 1e-3
WEIGHT_DECAY = 5e-4

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY
)


# ================================================================================
# 25. LR SCHEDULER
# ================================================================================

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="min",
    factor=0.5,
    patience=2
)


# ================================================================================
# 26. TRAINING SETTINGS
# ================================================================================

MAX_EPOCHS = 20
EARLY_STOPPING_PATIENCE = 5
GRADIENT_CLIP = 1.0

print("\n[19] TRAINING CONFIGURATION")
print("-" * 80)

print("Epochs:", MAX_EPOCHS)
print("Batch size:", BATCH_SIZE)
print("Learning rate:", LEARNING_RATE)
print("Weight decay:", WEIGHT_DECAY)
print("Label smoothing:", 0.05)
print("Early stopping:", EARLY_STOPPING_PATIENCE)
print("Gradient clipping:", GRADIENT_CLIP)


# ================================================================================
# 27. TRAINING STORAGE
# ================================================================================

history = []

best_val_accuracy = -1.0
best_val_loss = float("inf")

epochs_without_improvement = 0

best_model_path = os.path.join(
    OUTPUT_DIR,
    "step7L_temporal_cross_attention_best.pth"
)

final_model_path = os.path.join(
    OUTPUT_DIR,
    "step7L_temporal_cross_attention_final.pth"
)


# ================================================================================
# 28. TRAINING FUNCTIONS
# ================================================================================

def train_one_epoch(
    model,
    loader,
    optimizer,
    criterion,
    device
):

    model.train()

    total_loss = 0.0

    all_predictions = []
    all_labels = []

    for images, satellite, y in loader:

        images = images.to(
            device,
            non_blocking=True
        )

        satellite = satellite.to(
            device,
            non_blocking=True
        )

        y = y.to(
            device,
            non_blocking=True
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        logits = model(
            images,
            satellite
        )

        loss = criterion(
            logits,
            y
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            GRADIENT_CLIP
        )

        optimizer.step()

        total_loss += (
            loss.item()
            * images.size(0)
        )

        predictions = (
            torch.argmax(
                logits,
                dim=1
            )
        )

        all_predictions.extend(
            predictions.detach()
            .cpu()
            .numpy()
        )

        all_labels.extend(
            y.detach()
            .cpu()
            .numpy()
        )

    epoch_loss = (
        total_loss /
        len(loader.dataset)
    )

    epoch_accuracy = accuracy_score(
        all_labels,
        all_predictions
    )

    return epoch_loss, epoch_accuracy


# ================================================================================

def validate_one_epoch(
    model,
    loader,
    criterion,
    device
):

    model.eval()

    total_loss = 0.0

    all_predictions = []
    all_labels = []

    with torch.no_grad():

        for images, satellite, y in loader:

            images = images.to(
                device,
                non_blocking=True
            )

            satellite = satellite.to(
                device,
                non_blocking=True
            )

            y = y.to(
                device,
                non_blocking=True
            )

            logits = model(
                images,
                satellite
            )

            loss = criterion(
                logits,
                y
            )

            total_loss += (
                loss.item()
                * images.size(0)
            )

            predictions = (
                torch.argmax(
                    logits,
                    dim=1
                )
            )

            all_predictions.extend(
                predictions.cpu().numpy()
            )

            all_labels.extend(
                y.cpu().numpy()
            )

    epoch_loss = (
        total_loss /
        len(loader.dataset)
    )

    epoch_accuracy = accuracy_score(
        all_labels,
        all_predictions
    )

    return (
        epoch_loss,
        epoch_accuracy
    )


# ================================================================================
# 29. TRAINING LOOP
# ================================================================================

print("\n")
print("=" * 80)
print("STEP 7L TRAINING STARTED")
print("=" * 80)

for epoch in range(
    1,
    MAX_EPOCHS + 1
):

    train_loss, train_accuracy = train_one_epoch(
        model,
        train_loader,
        optimizer,
        criterion,
        device
    )

    val_loss, val_accuracy = validate_one_epoch(
        model,
        val_loader,
        criterion,
        device
    )

    scheduler.step(val_loss)

    current_lr = optimizer.param_groups[0]["lr"]

    history.append({

        "epoch": epoch,

        "train_loss": train_loss,

        "train_accuracy": train_accuracy,

        "val_loss": val_loss,

        "val_accuracy": val_accuracy,

        "learning_rate": current_lr

    })

    print(
        f"Epoch {epoch:02d}/{MAX_EPOCHS} | "
        f"Train Loss: {train_loss:.4f} | "
        f"Train Acc: {train_accuracy*100:.2f}% | "
        f"Val Loss: {val_loss:.4f} | "
        f"Val Acc: {val_accuracy*100:.2f}% | "
        f"LR: {current_lr:.6f}"
    )


    # ------------------------------------------------
    # SAVE BEST MODEL
    # ------------------------------------------------

    improved = False

    if val_accuracy > best_val_accuracy:

        improved = True

    elif (
        val_accuracy == best_val_accuracy
        and val_loss < best_val_loss
    ):

        improved = True


    if improved:

        best_val_accuracy = val_accuracy

        best_val_loss = val_loss

        epochs_without_improvement = 0

        torch.save(
            {
                "epoch": epoch,

                "model_state_dict":
                    model.state_dict(),

                "optimizer_state_dict":
                    optimizer.state_dict(),

                "scheduler_state_dict":
                    scheduler.state_dict(),

                "best_val_accuracy":
                    best_val_accuracy,

                "best_val_loss":
                    best_val_loss,

                "class_names":
                    CLASS_NAMES,

                "num_classes":
                    NUM_CLASSES,

                "architecture":
                    "Temporal BiLSTM + Cross Attention",

                "image_dim":
                    1792,

                "satellite_input_dim":
                    3,

                "satellite_timesteps":
                    10,

                "projection_dim":
                    256,

                "num_heads":
                    8
            },
            best_model_path
        )

        print(
            f"  ★ BEST MODEL SAVED "
            f"(Val Acc: {best_val_accuracy*100:.2f}%)"
        )

    else:

        epochs_without_improvement += 1


    # ------------------------------------------------
    # EARLY STOPPING
    # ------------------------------------------------

    if (
        epochs_without_improvement
        >= EARLY_STOPPING_PATIENCE
    ):

        print(
            "\nEarly stopping triggered."
        )

        break


# ================================================================================
# 30. SAVE FINAL MODEL
# ================================================================================

torch.save(
    {
        "model_state_dict":
            model.state_dict(),

        "class_names":
            CLASS_NAMES,

        "num_classes":
            NUM_CLASSES,

        "architecture":
            "Temporal BiLSTM + Cross Attention",

        "image_dim":
            1792,

        "satellite_input_dim":
            3,

        "satellite_timesteps":
            10,

        "projection_dim":
            256,

        "num_heads":
            8
    },
    final_model_path
)


# ================================================================================
# 31. SAVE TRAINING HISTORY
# ================================================================================

history_df = pd.DataFrame(history)

history_path = os.path.join(
    OUTPUT_DIR,
    "step7L_training_history.csv"
)

history_df.to_csv(
    history_path,
    index=False
)


# ================================================================================
# 32. LOAD BEST MODEL
# ================================================================================

print("\n[20] LOADING BEST MODEL")
print("-" * 80)

if not os.path.exists(best_model_path):

    raise FileNotFoundError(
        "❌ Best model was not saved."
    )

best_checkpoint = torch.load(
    best_model_path,
    map_location=device
)

model.load_state_dict(
    best_checkpoint["model_state_dict"]
)

print(
    "Best epoch:",
    best_checkpoint["epoch"]
)

print(
    "Best validation accuracy:",
    f"{best_checkpoint['best_val_accuracy']*100:.2f}%"
)

print(
    "Best validation loss:",
    f"{best_checkpoint['best_val_loss']:.4f}"
)


# ================================================================================
# 33. FINAL VALIDATION PREDICTIONS
# ================================================================================

print("\n[21] FINAL VALIDATION EVALUATION")
print("-" * 80)

model.eval()

all_predictions = []
all_true_labels = []
all_attention_weights = []

with torch.no_grad():

    for images, satellite, y in val_loader:

        images = images.to(device)

        satellite = satellite.to(device)

        logits, attention = model(
            images,
            satellite,
            return_attention=True
        )

        predictions = torch.argmax(
            logits,
            dim=1
        )

        all_predictions.extend(
            predictions.cpu().numpy()
        )

        all_true_labels.extend(
            y.numpy()
        )

        all_attention_weights.append(
            attention.cpu().numpy()
        )


all_predictions = np.array(
    all_predictions
)

all_true_labels = np.array(
    all_true_labels
)

all_attention_weights = np.concatenate(
    all_attention_weights,
    axis=0
)

final_accuracy = accuracy_score(
    all_true_labels,
    all_predictions
)

print(
    "Final best validation accuracy:",
    f"{final_accuracy*100:.2f}%"
)

print(
    "Attention shape:",
    all_attention_weights.shape
)

assert all_attention_weights.shape == (
    128,
    1,
    10
)


# ================================================================================
# 34. CLASSIFICATION REPORT
# ================================================================================

print("\n[22] CLASSIFICATION REPORT")
print("-" * 80)

report = classification_report(
    all_true_labels,
    all_predictions,
    labels=list(range(NUM_CLASSES)),
    target_names=CLASS_NAMES,
    zero_division=0
)

print(report)

report_path = os.path.join(
    OUTPUT_DIR,
    "step7L_classification_report.txt"
)

with open(
    report_path,
    "w"
) as f:

    f.write(report)


# ================================================================================
# 35. CONFUSION MATRIX
# ================================================================================

print("\n[23] CONFUSION MATRIX")
print("-" * 80)

cm = confusion_matrix(
    all_true_labels,
    all_predictions,
    labels=list(range(NUM_CLASSES))
)

cm_path = os.path.join(
    OUTPUT_DIR,
    "step7L_confusion_matrix.npy"
)

np.save(
    cm_path,
    cm
)

plt.figure(
    figsize=(12, 10)
)

plt.imshow(cm)

plt.title(
    "Step 7L — Temporal Cross-Attention Confusion Matrix"
)

plt.colorbar()

plt.xticks(
    range(NUM_CLASSES),
    CLASS_NAMES,
    rotation=90
)

plt.yticks(
    range(NUM_CLASSES),
    CLASS_NAMES
)

plt.xlabel("Predicted Class")

plt.ylabel("True Class")

for i in range(NUM_CLASSES):

    for j in range(NUM_CLASSES):

        plt.text(
            j,
            i,
            cm[i, j],
            ha="center",
            va="center"
        )

plt.tight_layout()

cm_plot_path = os.path.join(
    OUTPUT_DIR,
    "step7L_confusion_matrix.png"
)

plt.savefig(
    cm_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 36. TRAINING LOSS GRAPH
# ================================================================================

print("\n[24] GENERATING TRAINING GRAPHS")
print("-" * 80)

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    history_df["epoch"],
    history_df["train_loss"],
    marker="o",
    label="Train Loss"
)

plt.plot(
    history_df["epoch"],
    history_df["val_loss"],
    marker="o",
    label="Validation Loss"
)

plt.xlabel("Epoch")

plt.ylabel("Loss")

plt.title(
    "Step 7L — Training and Validation Loss"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

loss_plot_path = os.path.join(
    OUTPUT_DIR,
    "step7L_loss_curve.png"
)

plt.savefig(
    loss_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 37. ACCURACY GRAPH
# ================================================================================

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    history_df["epoch"],
    history_df["train_accuracy"] * 100,
    marker="o",
    label="Train Accuracy"
)

plt.plot(
    history_df["epoch"],
    history_df["val_accuracy"] * 100,
    marker="o",
    label="Validation Accuracy"
)

plt.xlabel("Epoch")

plt.ylabel("Accuracy (%)")

plt.title(
    "Step 7L — Training and Validation Accuracy"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

accuracy_plot_path = os.path.join(
    OUTPUT_DIR,
    "step7L_accuracy_curve.png"
)

plt.savefig(
    accuracy_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 38. TEMPORAL ATTENTION GRAPH
# ================================================================================

mean_attention = (
    all_attention_weights
    .mean(axis=0)
    .squeeze()
)

print(
    "\nMean temporal attention:",
    mean_attention
)

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    range(1, 11),
    mean_attention,
    marker="o"
)

plt.xticks(
    range(1, 11)
)

plt.xlabel(
    "Satellite Timestep"
)

plt.ylabel(
    "Mean Attention Weight"
)

plt.title(
    "Step 7L — Temporal Satellite Cross-Attention"
)

plt.grid(True)

plt.tight_layout()

attention_plot_path = os.path.join(
    OUTPUT_DIR,
    "step7L_temporal_attention.png"
)

plt.savefig(
    attention_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 39. SAVE ATTENTION VALUES
# ================================================================================

attention_csv_path = os.path.join(
    OUTPUT_DIR,
    "step7L_temporal_attention_values.csv"
)

attention_df = pd.DataFrame({

    "timestep": np.arange(1, 11),

    "mean_attention":
        mean_attention

})

attention_df.to_csv(
    attention_csv_path,
    index=False
)


# ================================================================================
# 40. SAVE FINAL REPORT
# ================================================================================

report_txt_path = os.path.join(
    OUTPUT_DIR,
    "step7L_final_training_report.txt"
)

with open(
    report_txt_path,
    "w"
) as f:

    f.write(
        "=" * 80 + "\n"
    )

    f.write(
        "STEP 7L — TEMPORAL CROSS-ATTENTION MULTIMODAL TRAINING\n"
    )

    f.write(
        "=" * 80 + "\n\n"
    )

    f.write(
        "DATASET\n"
    )

    f.write(
        "-" * 80 + "\n"
    )

    f.write(
        f"Total images: 640\n"
    )

    f.write(
        f"Train images: 512\n"
    )

    f.write(
        f"Validation images: 128\n"
    )

    f.write(
        f"Image embedding: (640,1792)\n"
    )

    f.write(
        f"Satellite sequence: (58,10,3)\n"
    )

    f.write(
        f"Mapped satellite sequence: (640,10,3)\n\n"
    )


    f.write(
        "ARCHITECTURE\n"
    )

    f.write(
        "-" * 80 + "\n"
    )

    f.write(
        "Image: EfficientNet-B4 embeddings, 1792-D\n"
    )

    f.write(
        "Image projection: 1792 -> 256\n"
    )

    f.write(
        "Satellite input: NDVI + NDRE + GNDVI\n"
    )

    f.write(
        "Satellite timesteps: 10\n"
    )

    f.write(
        "BiLSTM hidden size: 128\n"
    )

    f.write(
        "BiLSTM output: 256 per timestep\n"
    )

    f.write(
        "Cross-attention embed dimension: 256\n"
    )

    f.write(
        "Cross-attention heads: 8\n"
    )

    f.write(
        "Attention query: image\n"
    )

    f.write(
        "Attention key/value: 10 satellite timesteps\n"
    )

    f.write(
        "Attention output: 256\n"
    )

    f.write(
        "Fusion: 512 -> 256\n"
    )

    f.write(
        "Classifier: 256 -> 11\n\n"
    )


    f.write(
        "IMPORTANT MAPPING\n"
    )

    f.write(
        "-" * 80 + "\n"
    )

    f.write(
        "satellite_embedding_index was used for temporal mapping.\n"
    )

    f.write(
        "paired_satellite_embedding_index was NOT used for temporal mapping.\n"
    )

    f.write(
        "paired_satellite_embedding_index represents the 640-image row index.\n\n"
    )


    f.write(
        "RESULTS\n"
    )

    f.write(
        "-" * 80 + "\n"
    )

    f.write(
        f"Best validation accuracy: "
        f"{best_val_accuracy*100:.2f}%\n"
    )

    f.write(
        f"Best validation loss: "
        f"{best_val_loss:.4f}\n"
    )

    f.write(
        f"Final evaluation accuracy: "
        f"{final_accuracy*100:.2f}%\n"
    )


# ================================================================================
# 41. FINAL OUTPUT SUMMARY
# ================================================================================

print("\n")
print("=" * 80)
print("STEP 7L COMPLETED")
print("=" * 80)

print(
    f"\n★ BEST VALIDATION ACCURACY: "
    f"{best_val_accuracy*100:.2f}%"
)

print(
    f"★ BEST VALIDATION LOSS: "
    f"{best_val_loss:.4f}"
)

print(
    f"★ FINAL VALIDATION ACCURACY: "
    f"{final_accuracy*100:.2f}%"
)

print("\nSaved files:")
print("-" * 80)

print(
    "Best model:"
)
print(
    best_model_path
)

print(
    "\nFinal model:"
)
print(
    final_model_path
)

print(
    "\nTraining history:"
)
print(
    history_path
)

print(
    "\nClassification report:"
)
print(
    report_path
)

print(
    "\nConfusion matrix:"
)
print(
    cm_plot_path
)

print(
    "\nLoss graph:"
)
print(
    loss_plot_path
)

print(
    "\nAccuracy graph:"
)
print(
    accuracy_plot_path
)

print(
    "\nTemporal attention graph:"
)
print(
    attention_plot_path
)

print(
    "\nAttention values:"
)
print(
    attention_csv_path
)

print(
    "\nFinal report:"
)
print(
    report_txt_path
)

print("\n" + "=" * 80)
print("ALL STEP 7L CHECKS PASSED")
print("=" * 80)