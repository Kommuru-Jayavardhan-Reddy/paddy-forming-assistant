
#================================================================================
#STEP_7k — TEMPORAL CROSS-ATTENTION MULTIMODAL TRAINING_Improved
#================================================================================

import os
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report,
    f1_score
)

from sklearn.utils.class_weight import compute_class_weight

import torch
import torch.nn as nn

from torch.utils.data import (
    Dataset,
    DataLoader
)

from google.colab import drive


# ================================================================================
# 1. GOOGLE DRIVE
# ================================================================================

print("=" * 80)
print("STEP 7L — CONTROLLED IMPROVEMENT")
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

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("\n[3] DEVICE")
print("-" * 80)
print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# ================================================================================
# 4. PATHS
# ================================================================================

BASE_DIR = (
    "/content/drive/MyDrive/"
    "final year project/Real_world_test"
)

STEP5_DIR = os.path.join(
    BASE_DIR,
    "Step 5"
)

STEP7_DIR = os.path.join(
    BASE_DIR,
    "Step 7"
)

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

SATELLITE_SEQUENCE_PATH = os.path.join(
    STEP5_DIR,
    "bilstm_sequences.npy"
)

# NEW OUTPUT DIRECTORY
OUTPUT_DIR = os.path.join(
    STEP7_DIR,
    "Step7L_Controlled_81"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

print("\nOutput directory:")
print(OUTPUT_DIR)


# ================================================================================
# 5. REQUIRED FILES
# ================================================================================

print("\n[4] REQUIRED FILES")
print("-" * 80)

required_files = {
    "Dataset": DATASET_PATH,
    "Image embeddings": IMAGE_EMBEDDING_PATH,
    "Train indices": TRAIN_INDEX_PATH,
    "Validation indices": VAL_INDEX_PATH,
    "Satellite sequences": SATELLITE_SEQUENCE_PATH
}

for name, path in required_files.items():

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"\n❌ Missing {name}:\n{path}"
        )

    print("✓", name)
    print(" ", path)

print("\n✓ All required files found")


# ================================================================================
# 6. LOAD DATA
# ================================================================================

print("\n[5] LOADING DATA")
print("-" * 80)

df = pd.read_csv(
    DATASET_PATH
)

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
).astype(np.float32
)

print("Dataset shape:",
      df.shape)

print("Image embeddings:",
      image_embeddings.shape)

print("Train indices:",
      train_indices.shape)

print("Validation indices:",
      val_indices.shape)

print("Satellite sequences:",
      satellite_sequences.shape)


# ================================================================================
# 7. BASIC VALIDATION
# ================================================================================

print("\n[6] BASIC VALIDATION")
print("-" * 80)

assert len(df) == 640

assert image_embeddings.shape == (
    640,
    1792
)

assert satellite_sequences.shape == (
    58,
    10,
    3
)

assert len(train_indices) == 512

assert len(val_indices) == 128

print("✓ Dataset = 640")

print("✓ Image embeddings = (640,1792)")

print("✓ Satellite sequences = (58,10,3)")

print("✓ Train = 512")

print("✓ Validation = 128")


# ================================================================================
# 8. NUMERICAL VALIDATION
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

assert not np.isnan(
    image_embeddings
).any()

assert not np.isinf(
    image_embeddings
).any()

assert not np.isnan(
    satellite_sequences
).any()

assert not np.isinf(
    satellite_sequences
).any()

print("✓ No NaN values")
print("✓ No Inf values")


# ================================================================================
# 9. TRAIN / VALIDATION SPLIT
# ================================================================================

print("\n[8] TRAIN / VALIDATION SPLIT")
print("-" * 80)

train_set = set(
    train_indices.tolist()
)

val_set = set(
    val_indices.tolist()
)

overlap = train_set.intersection(
    val_set
)

print(
    "Train samples:",
    len(train_set)
)

print(
    "Validation samples:",
    len(val_set)
)

print(
    "Overlap:",
    len(overlap)
)

assert len(overlap) == 0

print("✓ No train/validation overlap")


# ================================================================================
# 10. CLASS DEFINITIONS
# ================================================================================

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

assert "label_11class" in df.columns

labels = (
    df["label_11class"]
    .astype(int)
    .to_numpy()
)

unique_labels = sorted(
    np.unique(labels).tolist()
)

assert unique_labels == list(
    range(NUM_CLASSES)
)

print("\n[9] CLASS DISTRIBUTION")
print("-" * 80)

for i, name in enumerate(
    CLASS_NAMES
):

    count = int(
        (labels == i).sum()
    )

    print(
        f"{i:2d} | "
        f"{name:<30} | "
        f"{count}"
    )


# ================================================================================
# 11. CORRECT SATELLITE MAPPING
# ================================================================================

print("\n[10] SATELLITE TEMPORAL MAPPING")
print("-" * 80)

assert (
    "satellite_embedding_index"
    in df.columns
)

assert (
    "nearest_satellite_field"
    in df.columns
)

satellite_indices = (
    df[
        "satellite_embedding_index"
    ]
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
    len(
        np.unique(
            satellite_indices
        )
    )
)

assert satellite_indices.min() >= 0

assert (
    satellite_indices.max()
    < len(satellite_sequences)
)


# ================================================================================
# 12. FIELD VALIDATION
# ================================================================================

field_mismatch_count = 0

for i in range(
    len(df)
):

    seq_idx = int(
        satellite_indices[i]
    )

    expected_field = (
        f"FIELD_{seq_idx + 1:02d}"
    )

    actual_field = str(
        df.iloc[i][
            "nearest_satellite_field"
        ]
    ).strip()

    if expected_field != actual_field:

        field_mismatch_count += 1

print(
    "Field mapping mismatches:",
    field_mismatch_count
)

assert field_mismatch_count == 0

print(
    "✓ Satellite field mapping correct"
)


# ================================================================================
# 13. BUILD IMAGE → SATELLITE SEQUENCES
# ================================================================================

image_satellite_sequences = (
    satellite_sequences[
        satellite_indices
    ].copy()
)

print(
    "Mapped satellite shape:",
    image_satellite_sequences.shape
)

assert image_satellite_sequences.shape == (
    640,
    10,
    3
)

print("✓ 640 images mapped")
print("✓ 10 timesteps")
print("✓ 3 features")
print("✓ NDVI + NDRE + GNDVI")


# ================================================================================
# 14. SATELLITE NORMALIZATION
# ================================================================================

print("\n[11] SATELLITE NORMALIZATION")
print("-" * 80)

train_satellite = (
    image_satellite_sequences[
        train_indices
    ]
)

train_satellite_flat = (
    train_satellite
    .reshape(-1, 3)
)

sat_mean = (
    train_satellite_flat
    .mean(axis=0)
)

sat_std = (
    train_satellite_flat
    .std(axis=0)
)

sat_std = np.maximum(
    sat_std,
    1e-6
)

image_satellite_sequences = (
    image_satellite_sequences
    - sat_mean.reshape(1, 1, 3)
) / sat_std.reshape(
    1, 1, 3
)

print(
    "Training satellite mean:",
    sat_mean
)

print(
    "Training satellite std:",
    sat_std
)

print(
    "✓ Train-only normalization applied"
)


# ================================================================================
# 15. PYTORCH DATASET
# ================================================================================

class PaddyMultimodalDataset(
    Dataset
):

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

        return len(
            self.labels
        )

    def __getitem__(
        self,
        idx
    ):

        return (
            self.image_embeddings[idx],
            self.satellite_sequences[idx],
            self.labels[idx]
        )


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

print("\n[12] DATASETS")
print("-" * 80)

print(
    "Train dataset:",
    len(train_dataset)
)

print(
    "Validation dataset:",
    len(val_dataset)
)


# ================================================================================
# 16. MILD CLASS BALANCING
# ================================================================================

print("\n[13] MILD CLASS BALANCING")
print("-" * 80)

train_labels = labels[
    train_indices
]

raw_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.arange(NUM_CLASSES),
    y=train_labels
).astype(np.float32)

# Mild square-root balancing
class_weights_np = np.sqrt(
    raw_weights
)

# Normalize mean weight to 1
class_weights_np = (
    class_weights_np /
    class_weights_np.mean()
)

class_weights = torch.tensor(
    class_weights_np,
    dtype=torch.float32,
    device=device
)

for i, weight in enumerate(
    class_weights_np
):

    print(
        f"{i:2d} | "
        f"{CLASS_NAMES[i]:<30} | "
        f"{weight:.4f}"
    )


# ================================================================================
# 17. TRAINING DATA LOADER
# IMPORTANT:
# WeightedRandomSampler REMOVED
# ================================================================================

print("\n[14] DATA LOADERS")
print("-" * 80)

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

print("✓ WeightedRandomSampler removed")
print("✓ Training loader: shuffle=True")
print("✓ Mild class weights retained")
print("✓ Validation loader unchanged")


# ================================================================================
# 18. MODEL
# ================================================================================

class TemporalCrossAttentionModel(
    nn.Module
):

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

            nn.GELU(),

            nn.Dropout(
                0.20
            )
        )

        # ------------------------------------------------
        # SATELLITE BiLSTM
        # ------------------------------------------------

        self.satellite_lstm = nn.LSTM(

            input_size=satellite_input_dim,

            hidden_size=lstm_hidden,

            num_layers=2,

            batch_first=True,

            dropout=0.20,

            bidirectional=True
        )

        self.satellite_projection = nn.Sequential(

            nn.Linear(
                lstm_hidden * 2,
                projection_dim
            ),

            nn.LayerNorm(
                projection_dim
            ),

            nn.GELU(),

            nn.Dropout(
                0.15
            )
        )

        # ------------------------------------------------
        # CROSS ATTENTION
        # ------------------------------------------------

        self.cross_attention = (
            nn.MultiheadAttention(

                embed_dim=projection_dim,

                num_heads=num_heads,

                dropout=0.10,

                batch_first=True
            )
        )

        self.attention_norm = (
            nn.LayerNorm(
                projection_dim
            )
        )

        # ------------------------------------------------
        # FUSION
        # ------------------------------------------------

        self.fusion = nn.Sequential(

            nn.Linear(
                projection_dim * 2,
                256
            ),

            nn.LayerNorm(
                256
            ),

            nn.GELU(),

            nn.Dropout(
                0.40
            ),

            nn.Linear(
                256,
                128
            ),

            nn.GELU(),

            nn.Dropout(
                0.25
            )
        )

        # ------------------------------------------------
        # CLASSIFIER
        # ------------------------------------------------

        self.classifier = nn.Linear(
            128,
            num_classes
        )


    def forward(
        self,
        image_embedding,
        satellite_sequence,
        return_attention=False
    ):

        # ------------------------------------------------
        # IMAGE
        # ------------------------------------------------

        image_features = (
            self.image_projection(
                image_embedding
            )
        )

        # ------------------------------------------------
        # SATELLITE
        # ------------------------------------------------

        satellite_lstm_output, _ = (
            self.satellite_lstm(
                satellite_sequence
            )
        )

        satellite_features = (
            self.satellite_projection(
                satellite_lstm_output
            )
        )

        # ------------------------------------------------
        # IMAGE = QUERY
        # SATELLITE = KEY / VALUE
        # ------------------------------------------------

        query = (
            image_features
            .unsqueeze(1)
        )

        key = satellite_features

        value = satellite_features

        attended_features, attention_weights = (
            self.cross_attention(
                query=query,
                key=key,
                value=value
            )
        )

        attended_features = (
            attended_features
            .squeeze(1)
        )

        # ------------------------------------------------
        # RESIDUAL CONNECTION
        # ------------------------------------------------

        attended_features = (
            self.attention_norm(
                attended_features
                + image_features
            )
        )

        # ------------------------------------------------
        # FUSION
        # ------------------------------------------------

        fused = torch.cat(
            [
                image_features,
                attended_features
            ],
            dim=1
        )

        fused = self.fusion(
            fused
        )

        # ------------------------------------------------
        # CLASSIFICATION
        # ------------------------------------------------

        logits = self.classifier(
            fused
        )

        if return_attention:

            return (
                logits,
                attention_weights
            )

        return logits


# ================================================================================
# 19. INITIALIZE MODEL
# ================================================================================

print("\n[15] INITIALIZING MODEL")
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

total_params = sum(
    p.numel()
    for p in model.parameters()
)

trainable_params = sum(
    p.numel()
    for p in model.parameters()
    if p.requires_grad
)

print(
    "\nTotal parameters:",
    total_params
)

print(
    "Trainable parameters:",
    trainable_params
)


# ================================================================================
# 20. FORWARD TEST
# ================================================================================

print("\n[16] FORWARD PASS TEST")
print("-" * 80)

sample_images, sample_satellite, sample_labels = next(
    iter(train_loader)
)

sample_images = sample_images.to(
    device
)

sample_satellite = sample_satellite.to(
    device
)

with torch.no_grad():

    sample_logits, sample_attention = (
        model(
            sample_images[:2],
            sample_satellite[:2],
            return_attention=True
        )
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

assert sample_logits.shape == (
    2,
    11
)

assert sample_attention.shape == (
    2,
    1,
    10
)

print("✓ Forward pass successful")


# ================================================================================
# 21. LOSS
# ================================================================================

LABEL_SMOOTHING = 0.01

criterion = nn.CrossEntropyLoss(

    weight=class_weights,

    label_smoothing=LABEL_SMOOTHING
)


# ================================================================================
# 22. OPTIMIZER
# ================================================================================

LEARNING_RATE = 3e-4

WEIGHT_DECAY = 5e-4

optimizer = torch.optim.AdamW(

    model.parameters(),

    lr=LEARNING_RATE,

    weight_decay=WEIGHT_DECAY
)


# ================================================================================
# 23. COSINE SCHEDULER
# ================================================================================

MAX_EPOCHS = 50

scheduler = (
    torch.optim.lr_scheduler
    .CosineAnnealingLR(
        optimizer,
        T_max=MAX_EPOCHS,
        eta_min=1e-6
    )
)

EARLY_STOPPING_PATIENCE = 12

GRADIENT_CLIP = 1.0


# ================================================================================
# 24. TRAINING CONFIGURATION
# ================================================================================

print("\n[17] TRAINING CONFIGURATION")
print("-" * 80)

print(
    "Epochs:",
    MAX_EPOCHS
)

print(
    "Batch size:",
    BATCH_SIZE
)

print(
    "Learning rate:",
    LEARNING_RATE
)

print(
    "Weight decay:",
    WEIGHT_DECAY
)

print(
    "Label smoothing:",
    LABEL_SMOOTHING
)

print(
    "Class balancing:",
    "sqrt balanced weights"
)

print(
    "WeightedRandomSampler:",
    "DISABLED"
)

print(
    "Scheduler:",
    "CosineAnnealingLR"
)

print(
    "Early stopping:",
    EARLY_STOPPING_PATIENCE
)

print(
    "Gradient clipping:",
    GRADIENT_CLIP
)


# ================================================================================
# 25. TRAIN FUNCTION
# ================================================================================

def train_one_epoch():

    model.train()

    total_loss = 0.0

    all_predictions = []

    all_labels = []

    for images, satellite, y in train_loader:

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

        predictions = torch.argmax(
            logits,
            dim=1
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
        len(train_loader.dataset)
    )

    epoch_accuracy = accuracy_score(
        all_labels,
        all_predictions
    )

    epoch_f1 = f1_score(
        all_labels,
        all_predictions,
        average="macro",
        zero_division=0
    )

    return (
        epoch_loss,
        epoch_accuracy,
        epoch_f1
    )


# ================================================================================
# 26. VALIDATION FUNCTION
# ================================================================================

@torch.no_grad()
def validate_one_epoch():

    model.eval()

    total_loss = 0.0

    all_predictions = []

    all_labels = []

    for images, satellite, y in val_loader:

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

        predictions = torch.argmax(
            logits,
            dim=1
        )

        all_predictions.extend(
            predictions
            .cpu()
            .numpy()
        )

        all_labels.extend(
            y.cpu()
            .numpy()
        )

    epoch_loss = (
        total_loss /
        len(val_loader.dataset)
    )

    epoch_accuracy = accuracy_score(
        all_labels,
        all_predictions
    )

    epoch_f1 = f1_score(
        all_labels,
        all_predictions,
        average="macro",
        zero_division=0
    )

    return (
        epoch_loss,
        epoch_accuracy,
        epoch_f1
    )


# ================================================================================
# 27. TRAINING LOOP
# ================================================================================

print("\n")
print("=" * 80)
print("STEP 7L CONTROLLED TRAINING STARTED")
print("=" * 80)

history = []

best_val_accuracy = -1.0

best_val_f1 = -1.0

best_val_loss = float(
    "inf"
)

epochs_without_improvement = 0

best_model_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_best.pth"
)

final_model_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_final.pth"
)


for epoch in range(
    1,
    MAX_EPOCHS + 1
):

    (
        train_loss,
        train_accuracy,
        train_f1
    ) = train_one_epoch()

    (
        val_loss,
        val_accuracy,
        val_f1
    ) = validate_one_epoch()

    scheduler.step()

    current_lr = (
        optimizer
        .param_groups[0]["lr"]
    )

    history.append({

        "epoch": epoch,

        "train_loss":
            train_loss,

        "train_accuracy":
            train_accuracy,

        "train_macro_f1":
            train_f1,

        "val_loss":
            val_loss,

        "val_accuracy":
            val_accuracy,

        "val_macro_f1":
            val_f1,

        "learning_rate":
            current_lr
    })

    print(
        f"Epoch {epoch:02d}/{MAX_EPOCHS} | "
        f"Train Loss: {train_loss:.4f} | "
        f"Train Acc: {train_accuracy*100:.2f}% | "
        f"Train F1: {train_f1*100:.2f}% | "
        f"Val Loss: {val_loss:.4f} | "
        f"Val Acc: {val_accuracy*100:.2f}% | "
        f"Val F1: {val_f1*100:.2f}% | "
        f"LR: {current_lr:.7f}"
    )

    # ------------------------------------------------
    # BEST MODEL
    # ------------------------------------------------

    improved = False

    if (
        val_accuracy
        > best_val_accuracy
    ):

        improved = True

    elif (
        val_accuracy
        == best_val_accuracy
        and val_f1
        > best_val_f1
    ):

        improved = True

    if improved:

        best_val_accuracy = (
            val_accuracy
        )

        best_val_f1 = (
            val_f1
        )

        best_val_loss = (
            val_loss
        )

        epochs_without_improvement = 0

        torch.save(
            {
                "epoch":
                    epoch,

                "model_state_dict":
                    model.state_dict(),

                "optimizer_state_dict":
                    optimizer.state_dict(),

                "scheduler_state_dict":
                    scheduler.state_dict(),

                "best_val_accuracy":
                    best_val_accuracy,

                "best_val_f1":
                    best_val_f1,

                "best_val_loss":
                    best_val_loss,

                "class_names":
                    CLASS_NAMES,

                "num_classes":
                    NUM_CLASSES,

                "architecture":
                    "Controlled Temporal BiLSTM + Residual Cross Attention",

                "image_dim":
                    1792,

                "satellite_input_dim":
                    3,

                "satellite_timesteps":
                    10,

                "projection_dim":
                    256,

                "num_heads":
                    8,

                "satellite_mean":
                    sat_mean.tolist(),

                "satellite_std":
                    sat_std.tolist(),

                "label_smoothing":
                    LABEL_SMOOTHING,

                "weight_decay":
                    WEIGHT_DECAY,

                "learning_rate":
                    LEARNING_RATE,

                "weighted_random_sampler":
                    False
            },

            best_model_path
        )

        print(
            f"  ★ BEST MODEL SAVED | "
            f"Val Acc: "
            f"{best_val_accuracy*100:.2f}% | "
            f"Macro-F1: "
            f"{best_val_f1*100:.2f}%"
        )

    else:

        epochs_without_improvement += 1

        print(
            f"  No improvement "
            f"({epochs_without_improvement}/"
            f"{EARLY_STOPPING_PATIENCE})"
        )

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
# 28. SAVE FINAL MODEL
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
            "Controlled Temporal BiLSTM + Residual Cross Attention",

        "image_dim":
            1792,

        "satellite_input_dim":
            3,

        "satellite_timesteps":
            10,

        "projection_dim":
            256,

        "num_heads":
            8,

        "satellite_mean":
            sat_mean.tolist(),

        "satellite_std":
            sat_std.tolist(),

        "label_smoothing":
            LABEL_SMOOTHING,

        "weight_decay":
            WEIGHT_DECAY,

        "learning_rate":
            LEARNING_RATE,

        "weighted_random_sampler":
            False
    },

    final_model_path
)

print(
    "\n✓ Final model saved:"
)

print(
    final_model_path
)


# ================================================================================
# 29. SAVE HISTORY
# ================================================================================

history_df = pd.DataFrame(
    history
)

history_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_training_history.csv"
)

history_df.to_csv(
    history_path,
    index=False
)

print(
    "✓ Training history saved"
)


# ================================================================================
# 30. LOAD BEST MODEL
# IMPORTANT:
# PyTorch 2.6+ compatible
# ================================================================================

print("\n[18] LOADING BEST MODEL")
print("-" * 80)

if not os.path.exists(
    best_model_path
):

    raise FileNotFoundError(
        "Best model checkpoint not found:\n"
        + best_model_path
    )

checkpoint = torch.load(
    best_model_path,
    map_location=device,
    weights_only=False
)

model.load_state_dict(
    checkpoint[
        "model_state_dict"
    ]
)

print(
    "Best epoch:",
    checkpoint["epoch"]
)

print(
    "Best validation accuracy:",
    f"{checkpoint['best_val_accuracy']*100:.2f}%"
)

print(
    "Best validation Macro-F1:",
    f"{checkpoint['best_val_f1']*100:.2f}%"
)

print(
    "Best validation loss:",
    f"{checkpoint['best_val_loss']:.4f}"
)


# ================================================================================
# 31. FINAL VALIDATION PREDICTIONS
# ================================================================================

print("\n[19] FINAL VALIDATION EVALUATION")
print("-" * 80)

model.eval()

all_predictions = []

all_true_labels = []

all_attention_weights = []

with torch.no_grad():

    for images, satellite, y in val_loader:

        images = images.to(
            device
        )

        satellite = satellite.to(
            device
        )

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
            predictions
            .cpu()
            .numpy()
        )

        all_true_labels.extend(
            y.numpy()
        )

        all_attention_weights.append(
            attention
            .cpu()
            .numpy()
        )


all_predictions = np.array(
    all_predictions
)

all_true_labels = np.array(
    all_true_labels
)

all_attention_weights = (
    np.concatenate(
        all_attention_weights,
        axis=0
    )
)


# ================================================================================
# 32. FINAL METRICS
# ================================================================================

final_accuracy = accuracy_score(
    all_true_labels,
    all_predictions
)

final_macro_f1 = f1_score(
    all_true_labels,
    all_predictions,
    average="macro",
    zero_division=0
)

correct_predictions = int(
    np.sum(
        all_predictions
        == all_true_labels
    )
)

total_validation = len(
    all_true_labels
)

incorrect_predictions = (
    total_validation
    - correct_predictions
)

print(
    "\nCorrect predictions:",
    f"{correct_predictions}/{total_validation}"
)

print(
    "Incorrect predictions:",
    f"{incorrect_predictions}/{total_validation}"
)

print(
    "Final validation accuracy:",
    f"{final_accuracy*100:.2f}%"
)

print(
    "Final validation Macro-F1:",
    f"{final_macro_f1*100:.2f}%"
)

print(
    "Best validation accuracy:",
    f"{best_val_accuracy*100:.2f}%"
)

print(
    "Best validation Macro-F1:",
    f"{best_val_f1*100:.2f}%"
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
# 33. TARGET CHECK
# ================================================================================

print("\n[20] TARGET CHECK")
print("-" * 80)

if best_val_accuracy >= 0.8125:

    print(
        "🎯 TARGET ACHIEVED!"
    )

    print(
        f"Validation accuracy = "
        f"{best_val_accuracy*100:.2f}%"
    )

    print(
        "At least 104/128 validation "
        "samples are correctly classified."
    )

elif best_val_accuracy >= 0.8046875:

    print(
        "✓ ABOVE 80% ACHIEVED"
    )

    print(
        f"Validation accuracy = "
        f"{best_val_accuracy*100:.2f}%"
    )

    print(
        "81% target needs at least "
        "104/128 correct predictions."
    )

else:

    print(
        "⚠ 81% target not reached yet."
    )

    print(
        f"Best accuracy = "
        f"{best_val_accuracy*100:.2f}%"
    )

    print(
        "Current target requires "
        "104/128 correct predictions."
    )


# ================================================================================
# 34. CLASSIFICATION REPORT
# ================================================================================

print("\n[21] CLASSIFICATION REPORT")
print("-" * 80)

report = classification_report(
    all_true_labels,
    all_predictions,
    labels=list(
        range(NUM_CLASSES)
    ),
    target_names=CLASS_NAMES,
    zero_division=0,
    digits=4
)

print(report)

report_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_classification_report.txt"
)

with open(
    report_path,
    "w"
) as f:

    f.write(report)


# ================================================================================
# 35. CONFUSION MATRIX
# ================================================================================

print("\n[22] CONFUSION MATRIX")
print("-" * 80)

cm = confusion_matrix(
    all_true_labels,
    all_predictions,
    labels=list(
        range(NUM_CLASSES)
    )
)

cm_npy_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_confusion_matrix.npy"
)

np.save(
    cm_npy_path,
    cm
)

plt.figure(
    figsize=(12, 10)
)

plt.imshow(cm)

plt.title(
    "Step 7L — Controlled Improvement Confusion Matrix"
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

plt.xlabel(
    "Predicted Class"
)

plt.ylabel(
    "True Class"
)

for i in range(
    NUM_CLASSES
):

    for j in range(
        NUM_CLASSES
    ):

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
    "step7L_controlled_confusion_matrix.png"
)

plt.savefig(
    cm_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 36. LOSS GRAPH
# ================================================================================

print("\n[23] TRAINING GRAPHS")
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

plt.xlabel(
    "Epoch"
)

plt.ylabel(
    "Loss"
)

plt.title(
    "Step 7L — Training and Validation Loss"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

loss_plot_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_loss_curve.png"
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

plt.axhline(
    81.0,
    linestyle="--",
    label="81% Target"
)

plt.xlabel(
    "Epoch"
)

plt.ylabel(
    "Accuracy (%)"
)

plt.title(
    "Step 7L — Training and Validation Accuracy"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

accuracy_plot_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_accuracy_curve.png"
)

plt.savefig(
    accuracy_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 38. MACRO F1 GRAPH
# ================================================================================

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    history_df["epoch"],
    history_df["train_macro_f1"] * 100,
    marker="o",
    label="Train Macro-F1"
)

plt.plot(
    history_df["epoch"],
    history_df["val_macro_f1"] * 100,
    marker="o",
    label="Validation Macro-F1"
)

plt.xlabel(
    "Epoch"
)

plt.ylabel(
    "Macro-F1 (%)"
)

plt.title(
    "Step 7L — Macro-F1"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

f1_plot_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_macro_f1_curve.png"
)

plt.savefig(
    f1_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 39. TEMPORAL ATTENTION
# ================================================================================

mean_attention = (
    all_attention_weights
    .mean(axis=0)
    .squeeze()
)

print("\n[24] MEAN TEMPORAL ATTENTION")
print("-" * 80)

print(
    mean_attention
)

print(
    "Attention sum:",
    mean_attention.sum()
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
    "step7L_controlled_temporal_attention.png"
)

plt.savefig(
    attention_plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ================================================================================
# 40. SAVE ATTENTION VALUES
# ================================================================================

attention_csv_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_temporal_attention_values.csv"
)

attention_df = pd.DataFrame({

    "timestep":
        np.arange(1, 11),

    "mean_attention":
        mean_attention

})

attention_df.to_csv(
    attention_csv_path,
    index=False
)


# ================================================================================
# 41. SAVE FINAL REPORT
# ================================================================================

final_report_path = os.path.join(
    OUTPUT_DIR,
    "step7L_controlled_final_training_report.txt"
)

with open(
    final_report_path,
    "w"
) as f:

    f.write(
        "=" * 80 + "\n"
    )

    f.write(
        "STEP 7L — CONTROLLED IMPROVEMENT\n"
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
        "Total images: 640\n"
    )

    f.write(
        "Train images: 512\n"
    )

    f.write(
        "Validation images: 128\n"
    )

    f.write(
        "Image embedding: (640,1792)\n"
    )

    f.write(
        "Satellite sequence: (58,10,3)\n"
    )

    f.write(
        "Mapped sequence: (640,10,3)\n\n"
    )

    f.write(
        "CONTROLLED TRAINING CHANGES\n"
    )

    f.write(
        "-" * 80 + "\n"
    )

    f.write(
        "Train-only satellite normalization\n"
    )

    f.write(
        "Moderated sqrt class weights\n"
    )

    f.write(
        "WeightedRandomSampler: disabled\n"
    )

    f.write(
        "Shuffle training batches: enabled\n"
    )

    f.write(
        "Learning rate: 0.0003\n"
    )

    f.write(
        "Weight decay: 0.0005\n"
    )

    f.write(
        "Label smoothing: 0.01\n"
    )

    f.write(
        "CosineAnnealingLR\n"
    )

    f.write(
        "Maximum epochs: 50\n"
    )

    f.write(
        "Early stopping patience: 12\n\n"
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
        f"Best validation Macro-F1: "
        f"{best_val_f1*100:.2f}%\n"
    )

    f.write(
        f"Best validation loss: "
        f"{best_val_loss:.4f}\n"
    )

    f.write(
        f"Final validation accuracy: "
        f"{final_accuracy*100:.2f}%\n"
    )

    f.write(
        f"Final validation Macro-F1: "
        f"{final_macro_f1*100:.2f}%\n"
    )

    f.write(
        f"Correct validation predictions: "
        f"{correct_predictions}/128\n"
    )

    f.write(
        f"Incorrect validation predictions: "
        f"{incorrect_predictions}/128\n"
    )


# ================================================================================
# 42. FINAL SUMMARY
# ================================================================================

print("\n")
print("=" * 80)
print("STEP 7L CONTROLLED IMPROVEMENT COMPLETED")
print("=" * 80)

print(
    f"\n★ BEST VALIDATION ACCURACY: "
    f"{best_val_accuracy*100:.2f}%"
)

print(
    f"★ BEST VALIDATION MACRO-F1: "
    f"{best_val_f1*100:.2f}%"
)

print(
    f"★ FINAL VALIDATION ACCURACY: "
    f"{final_accuracy*100:.2f}%"
)

print(
    f"★ FINAL VALIDATION MACRO-F1: "
    f"{final_macro_f1*100:.2f}%"
)

print(
    f"\n★ CORRECT: "
    f"{correct_predictions}/128"
)

print(
    f"★ INCORRECT: "
    f"{incorrect_predictions}/128"
)

print("\nOutput folder:")
print(
    OUTPUT_DIR
)

print("\nBest model:")
print(
    best_model_path
)

print("\nClassification report:")
print(
    report_path
)

print("\nConfusion matrix:")
print(
    cm_plot_path
)

print("\n" + "=" * 80)
print("ALL STEP 7L CONTROLLED CHECKS PASSED")
print("=" * 80)