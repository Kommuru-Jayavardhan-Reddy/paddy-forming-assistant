# =============================================================================
# STEP 9 — FINAL EVALUATION OF SELECTED STEP 7 CONTROLLED MODEL
# =============================================================================
# READ-ONLY EVALUATION
#
# IMPORTANT:
# This code evaluates the EXACT Step 7 model selected as final:
#
# step7L_controlled_best.pth
#
# It does NOT:
# - retrain the model
# - modify Step 7
# - regenerate mapping
# - regenerate train/validation split
# - change the checkpoint
#
# It produces:
# - overall metrics
# - class-wise metrics
# - confusion matrix
# - all predictions
# - correct predictions
# - wrong predictions
# - confidence analysis
# - temporal attention analysis
# - final evaluation report
# =============================================================================

import os
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

from torch.utils.data import Dataset, DataLoader


# =============================================================================
# 1. GOOGLE DRIVE
# =============================================================================

from google.colab import drive

drive.mount("/content/drive")

print("=" * 90)
print("STEP 9 — FINAL MULTIMODAL MODEL EVALUATION")
print("=" * 90)


# =============================================================================
# 2. DEVICE
# =============================================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("\n[1] DEVICE")
print("-" * 90)
print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# =============================================================================
# 3. PATHS
# =============================================================================

BASE = "/content/drive/MyDrive/final year project/Real_world_test"

STEP5 = os.path.join(BASE, "Step 5")
STEP7 = os.path.join(BASE, "Step 7")

OUTPUT_DIR = os.path.join(
    STEP7,
    "Step9_Final_Controlled_Evaluation"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# -----------------------------------------------------------------------------
# REQUIRED FILES
# -----------------------------------------------------------------------------

IMAGE_EMBEDDINGS_FILE = os.path.join(
    STEP7,
    "step7_FINAL_image_embeddings_1792.npy"
)

SATELLITE_FILE = os.path.join(
    STEP5,
    "bilstm_sequences.npy"
)

MAPPING_FILE = os.path.join(
    STEP7,
    "step8B_final_rectified_640_mapping.csv"
)

DATASET_FILE = os.path.join(
    STEP7,
    "step7I_final_11class_multimodal_dataset.csv"
)

TRAIN_INDICES_FILE = os.path.join(
    STEP7,
    "step7I_train_indices.npy"
)

VAL_INDICES_FILE = os.path.join(
    STEP7,
    "step7I_val_indices.npy"
)

# ============================================================================
# CORRECT FINAL CHECKPOINT
# ============================================================================
#
# IMPORTANT:
# DO NOT USE:
# Step7L_Temporal_CrossAttention_Improved/step7L_improved_best.pth
#
# USE:
# Step7L_Controlled_81/step7L_controlled_best.pth
#
# ============================================================================

CHECKPOINT_FILE = os.path.join(
    STEP7,
    "Step7L_Controlled_81",
    "step7L_controlled_best.pth"
)


# =============================================================================
# 4. REQUIRED FILE CHECK
# =============================================================================

print("\n[2] REQUIRED FILES")
print("-" * 90)

required_files = {
    "Image embeddings": IMAGE_EMBEDDINGS_FILE,
    "Satellite sequences": SATELLITE_FILE,
    "Rectified mapping": MAPPING_FILE,
    "Dataset": DATASET_FILE,
    "Train indices": TRAIN_INDICES_FILE,
    "Validation indices": VAL_INDICES_FILE,
    "FINAL CONTROLLED CHECKPOINT": CHECKPOINT_FILE
}

all_files_exist = True

for name, path in required_files.items():

    if os.path.exists(path):

        size_mb = os.path.getsize(path) / (1024 * 1024)

        print(f"✓ {name}")
        print(f"  {path}")
        print(f"  Size: {size_mb:.2f} MB")

    else:

        print(f"✗ MISSING: {name}")
        print(f"  {path}")

        all_files_exist = False


if not all_files_exist:

    raise FileNotFoundError(
        "One or more required files are missing. "
        "Do not continue until paths are correct."
    )


# =============================================================================
# 5. LOAD DATA
# =============================================================================

print("\n[3] LOADING DATA")
print("-" * 90)

image_embeddings = np.load(
    IMAGE_EMBEDDINGS_FILE
).astype(np.float32)

satellite_sequences = np.load(
    SATELLITE_FILE
).astype(np.float32)

mapping_df = pd.read_csv(
    MAPPING_FILE
)

dataset_df = pd.read_csv(
    DATASET_FILE
)

train_indices = np.load(
    TRAIN_INDICES_FILE
)

val_indices = np.load(
    VAL_INDICES_FILE
)

print(
    "Image embeddings shape:",
    image_embeddings.shape
)

print(
    "Satellite sequences shape:",
    satellite_sequences.shape
)

print(
    "Mapping shape:",
    mapping_df.shape
)

print(
    "Dataset shape:",
    dataset_df.shape
)

print(
    "Train indices:",
    train_indices.shape
)

print(
    "Validation indices:",
    val_indices.shape
)


# =============================================================================
# 6. BASIC DATA VALIDATION
# =============================================================================

print("\n[4] DATA VALIDATION")
print("-" * 90)

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

assert image_embeddings.shape == (640, 1792)
assert satellite_sequences.shape == (58, 10, 3)

assert len(mapping_df) == 640
assert len(dataset_df) == 640

print("✓ Image data valid")
print("✓ Satellite data valid")
print("✓ 640 image samples")
print("✓ 58 satellite fields")
print("✓ 10 timesteps × 3 features")


# =============================================================================
# 7. TRAIN / VALIDATION SPLIT CHECK
# =============================================================================

print("\n[5] TRAIN / VALIDATION SPLIT")
print("-" * 90)

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

assert len(train_set) == 512
assert len(val_set) == 128
assert len(overlap) == 0

print("✓ No train/validation overlap")


# =============================================================================
# 8. LABEL EXTRACTION
# =============================================================================

print("\n[6] LABEL DETECTION")
print("-" * 90)

possible_label_columns = [
    "disease_label",
    "disease_class",
    "label",
    "class_name",
    "class"
]

label_column = None

for col in possible_label_columns:

    if col in dataset_df.columns:

        label_column = col
        break


if label_column is not None:

    print(
        "Label source:",
        label_column
    )

    raw_labels = (
        dataset_df[label_column]
        .astype(str)
        .str.strip()
    )

else:

    print(
        "No explicit disease label column found."
    )

    print(
        "Attempting to extract disease class from image_path..."
    )

    if "image_path" not in dataset_df.columns:

        raise ValueError(
            "No disease label column and no image_path column found."
        )

    def extract_label(path):

        path = str(path).replace("\\", "/")

        parts = [
            p.strip()
            for p in path.split("/")
            if p.strip()
        ]

        disease_classes = {
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
        }

        for part in reversed(parts):

            if part in disease_classes:

                return part

        return None


    raw_labels = (
        dataset_df["image_path"]
        .apply(extract_label)
    )

    print(
        "Label source: image_path"
    )


# =============================================================================
# 9. LABEL VALIDATION
# =============================================================================

print("\n[7] LABEL VALIDATION")
print("-" * 90)

if raw_labels.isna().any():

    missing_count = raw_labels.isna().sum()

    raise ValueError(
        f"{missing_count} samples have missing labels."
    )


class_names = sorted(
    raw_labels.unique().tolist()
)

print(
    "Total labeled samples:",
    len(raw_labels)
)

print(
    "Classes present:",
    len(class_names)
)

for i, cls in enumerate(class_names):

    print(
        f"{i:2d} | {cls}"
    )


assert len(class_names) == 11
assert len(raw_labels) == 640


# =============================================================================
# 10. CLASS → INTEGER MAPPING
# =============================================================================

label_to_index = {
    cls: i
    for i, cls in enumerate(class_names)
}

index_to_label = {
    i: cls
    for cls, i in label_to_index.items()
}

true_labels = np.array([
    label_to_index[x]
    for x in raw_labels
])


# =============================================================================
# 11. SATELLITE INDEX DETECTION
# =============================================================================

print("\n[8] SATELLITE MAPPING")
print("-" * 90)

possible_satellite_columns = [
    "satellite_embedding_index",
    "paired_satellite_embedding_index",
    "sequence_index",
    "embedding_index"
]

satellite_index_column = None

for col in possible_satellite_columns:

    if col in dataset_df.columns:

        satellite_index_column = col
        break


if satellite_index_column is None:

    raise ValueError(
        "Could not find satellite index column."
    )


print(
    "Satellite index column:",
    satellite_index_column
)

satellite_indices = (
    dataset_df[satellite_index_column]
    .astype(int)
    .values
)

print(
    "Satellite index min:",
    satellite_indices.min()
)

print(
    "Satellite index max:",
    satellite_indices.max()
)

assert satellite_indices.min() >= 0
assert satellite_indices.max() < len(satellite_sequences)

print("✓ All satellite indices valid")


# =============================================================================
# 12. BUILD 640 TEMPORAL SEQUENCES
# =============================================================================

print("\n[9] TEMPORAL SATELLITE EXPANSION")
print("-" * 90)

expanded_satellite = (
    satellite_sequences[satellite_indices]
)

print(
    "Expanded satellite shape:",
    expanded_satellite.shape
)

assert expanded_satellite.shape == (
    640,
    10,
    3
)

print(
    "✓ 640 images mapped to 10×3 temporal satellite sequences"
)


# =============================================================================
# 13. MODEL DEFINITION
# =============================================================================
#
# This matches the architecture used by the Controlled Step 7 model:
#
# Image:
#   1792 → 256
#
# Satellite:
#   3 → BiLSTM hidden 128
#   Bidirectional → 256
#   → 256 projection
#
# Cross attention:
#   256 dimensions
#   8 heads
#
# Fusion:
#   256 + 256 = 512
#   512 → 256 → 128
#
# Classifier:
#   128 → 11
#
# =============================================================================

print("\n[10] MODEL ARCHITECTURE")
print("-" * 90)


class TemporalCrossAttentionModel(nn.Module):

    def __init__(
        self,
        image_dim=1792,
        hidden_dim=128,
        attention_dim=256,
        num_heads=8,
        num_classes=11
    ):

        super().__init__()

        # ---------------------------------------------------------
        # IMAGE BRANCH
        # ---------------------------------------------------------

        self.image_projection = nn.Sequential(

            nn.Linear(
                image_dim,
                attention_dim
            ),

            nn.LayerNorm(
                attention_dim
            ),

            nn.GELU(),

            nn.Dropout(
                0.2
            )
        )

        # ---------------------------------------------------------
        # SATELLITE TEMPORAL BRANCH
        # ---------------------------------------------------------

        self.satellite_lstm = nn.LSTM(

            input_size=3,

            hidden_size=hidden_dim,

            num_layers=2,

            batch_first=True,

            dropout=0.2,

            bidirectional=True
        )

        self.satellite_projection = nn.Sequential(

            nn.Linear(
                hidden_dim * 2,
                attention_dim
            ),

            nn.LayerNorm(
                attention_dim
            ),

            nn.GELU(),

            nn.Dropout(
                0.15
            )
        )

        # ---------------------------------------------------------
        # CROSS ATTENTION
        # ---------------------------------------------------------

        self.cross_attention = nn.MultiheadAttention(

            embed_dim=attention_dim,

            num_heads=num_heads,

            dropout=0.1,

            batch_first=True
        )

        self.attention_norm = nn.LayerNorm(
            attention_dim
        )

        # ---------------------------------------------------------
        # FUSION
        # ---------------------------------------------------------

        self.fusion = nn.Sequential(

            nn.Linear(
                512,
                256
            ),

            nn.LayerNorm(
                256
            ),

            nn.GELU(),

            nn.Dropout(
                0.4
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

        # ---------------------------------------------------------
        # CLASSIFIER
        # ---------------------------------------------------------

        self.classifier = nn.Linear(
            128,
            num_classes
        )


    def forward(
        self,
        image,
        satellite
    ):

        # Image features
        image_feat = self.image_projection(
            image
        )

        # Satellite temporal features
        satellite_out, _ = self.satellite_lstm(
            satellite
        )

        satellite_feat = self.satellite_projection(
            satellite_out
        )

        # Image = Query
        query = image_feat.unsqueeze(1)

        # Satellite = Key + Value
        attended, attention = self.cross_attention(
            query,
            satellite_feat,
            satellite_feat
        )

        # Residual
        attended = self.attention_norm(
            attended + query
        )

        attended = attended.squeeze(1)

        # Fusion
        fused = torch.cat(
            [
                image_feat,
                attended
            ],
            dim=1
        )

        fused = self.fusion(
            fused
        )

        # Classification
        logits = self.classifier(
            fused
        )

        return logits, attention


# =============================================================================
# 14. INITIALIZE MODEL
# =============================================================================

model = TemporalCrossAttentionModel(
    image_dim=1792,
    hidden_dim=128,
    attention_dim=256,
    num_heads=8,
    num_classes=11
)

model = model.to(device)

print(model)

total_parameters = sum(
    p.numel()
    for p in model.parameters()
)

print(
    "\nTotal parameters:",
    total_parameters
)


# =============================================================================
# 15. LOAD EXACT CONTROLLED CHECKPOINT
# =============================================================================

print("\n[11] LOADING FINAL CONTROLLED CHECKPOINT")
print("-" * 90)

print(
    "Checkpoint:",
    CHECKPOINT_FILE
)

checkpoint = torch.load(
    CHECKPOINT_FILE,
    map_location=device,
    weights_only=False
)

print(
    "✓ Checkpoint loaded"
)

print(
    "Checkpoint epoch:",
    checkpoint.get("epoch")
)

print(
    "Checkpoint best validation accuracy:",
    checkpoint.get("best_val_accuracy")
)

print(
    "Checkpoint best validation F1:",
    checkpoint.get(
        "best_val_f1",
        checkpoint.get("best_val_macro_f1")
    )
)

print(
    "Checkpoint architecture:",
    checkpoint.get("architecture")
)


# =============================================================================
# 16. LOAD MODEL WEIGHTS
# =============================================================================

state_dict = checkpoint["model_state_dict"]

missing_keys, unexpected_keys = model.load_state_dict(
    state_dict,
    strict=False
)

print(
    "Missing keys:",
    missing_keys
)

print(
    "Unexpected keys:",
    unexpected_keys
)

if len(missing_keys) != 0:

    raise RuntimeError(
        "Model checkpoint has missing parameters."
    )

if len(unexpected_keys) != 0:

    raise RuntimeError(
        "Model checkpoint has unexpected parameters."
    )

print(
    "✓ Exact model parameters loaded"
)


# =============================================================================
# 17. EVALUATION DATASET
# =============================================================================

class MultimodalEvaluationDataset(Dataset):

    def __init__(
        self,
        image_data,
        satellite_data,
        labels
    ):

        self.image_data = torch.tensor(
            image_data,
            dtype=torch.float32
        )

        self.satellite_data = torch.tensor(
            satellite_data,
            dtype=torch.float32
        )

        self.labels = torch.tensor(
            labels,
            dtype=torch.long
        )


    def __len__(self):

        return len(self.labels)


    def __getitem__(self, idx):

        return (
            self.image_data[idx],
            self.satellite_data[idx],
            self.labels[idx]
        )


# =============================================================================
# 18. FULL 640-SAMPLE EVALUATION
# =============================================================================

print("\n[12] RUNNING FINAL INFERENCE")
print("-" * 90)

eval_dataset = MultimodalEvaluationDataset(
    image_embeddings,
    expanded_satellite,
    true_labels
)

eval_loader = DataLoader(
    eval_dataset,
    batch_size=32,
    shuffle=False,
    num_workers=0
)

model.eval()

all_logits = []
all_predictions = []
all_probabilities = []
all_confidences = []
all_attention = []
all_true_labels = []

with torch.no_grad():

    for (
        images,
        satellites,
        labels
    ) in eval_loader:

        images = images.to(device)
        satellites = satellites.to(device)

        logits, attention = model(
            images,
            satellites
        )

        probabilities = torch.softmax(
            logits,
            dim=1
        )

        confidence, predictions = torch.max(
            probabilities,
            dim=1
        )

        all_logits.append(
            logits.cpu().numpy()
        )

        all_predictions.append(
            predictions.cpu().numpy()
        )

        all_probabilities.append(
            probabilities.cpu().numpy()
        )

        all_confidences.append(
            confidence.cpu().numpy()
        )

        all_attention.append(
            attention.squeeze(1).cpu().numpy()
        )

        all_true_labels.append(
            labels.cpu().numpy()
        )


logits = np.concatenate(
    all_logits,
    axis=0
)

predictions = np.concatenate(
    all_predictions,
    axis=0
)

probabilities = np.concatenate(
    all_probabilities,
    axis=0
)

confidences = np.concatenate(
    all_confidences,
    axis=0
)

attention = np.concatenate(
    all_attention,
    axis=0
)

true_labels = np.concatenate(
    all_true_labels,
    axis=0
)


print(
    "Logits shape:",
    logits.shape
)

print(
    "Predictions shape:",
    predictions.shape
)

print(
    "Probabilities shape:",
    probabilities.shape
)

print(
    "Confidence shape:",
    confidences.shape
)

print(
    "Attention shape:",
    attention.shape
)


# =============================================================================
# 19. NUMERICAL VALIDATION
# =============================================================================

print("\n[13] NUMERICAL VALIDATION")
print("-" * 90)

print(
    "Logits NaN:",
    np.isnan(logits).sum()
)

print(
    "Logits Inf:",
    np.isinf(logits).sum()
)

print(
    "Probability NaN:",
    np.isnan(probabilities).sum()
)

print(
    "Probability Inf:",
    np.isinf(probabilities).sum()
)

print(
    "Attention NaN:",
    np.isnan(attention).sum()
)

print(
    "Attention Inf:",
    np.isinf(attention).sum()
)

attention_sums = attention.sum(
    axis=1
)

print(
    "Attention row sum min:",
    attention_sums.min()
)

print(
    "Attention row sum max:",
    attention_sums.max()
)

assert not np.isnan(logits).any()
assert not np.isinf(logits).any()

assert not np.isnan(probabilities).any()
assert not np.isinf(probabilities).any()

assert not np.isnan(attention).any()
assert not np.isinf(attention).any()

assert np.allclose(
    attention_sums,
    1.0,
    atol=1e-4
)

print("✓ Numerical validation passed")


# =============================================================================
# 20. OVERALL PERFORMANCE
# =============================================================================

print("\n[14] OVERALL PERFORMANCE")
print("-" * 90)

accuracy = accuracy_score(
    true_labels,
    predictions
)

macro_precision = precision_score(
    true_labels,
    predictions,
    average="macro",
    zero_division=0
)

macro_recall = recall_score(
    true_labels,
    predictions,
    average="macro",
    zero_division=0
)

macro_f1 = f1_score(
    true_labels,
    predictions,
    average="macro",
    zero_division=0
)

weighted_precision = precision_score(
    true_labels,
    predictions,
    average="weighted",
    zero_division=0
)

weighted_recall = recall_score(
    true_labels,
    predictions,
    average="weighted",
    zero_division=0
)

weighted_f1 = f1_score(
    true_labels,
    predictions,
    average="weighted",
    zero_division=0
)

print(
    f"Accuracy           : {accuracy:.4f} "
    f"({accuracy * 100:.2f}%)"
)

print(
    f"Macro Precision    : {macro_precision:.4f}"
)

print(
    f"Macro Recall       : {macro_recall:.4f}"
)

print(
    f"Macro F1           : {macro_f1:.4f}"
)

print(
    f"Weighted Precision : {weighted_precision:.4f}"
)

print(
    f"Weighted Recall    : {weighted_recall:.4f}"
)

print(
    f"Weighted F1        : {weighted_f1:.4f}"
)


# =============================================================================
# 21. CLASSIFICATION REPORT
# =============================================================================

print("\n[15] CLASSIFICATION REPORT")
print("-" * 90)

report_text = classification_report(
    true_labels,
    predictions,
    labels=list(range(len(class_names))),
    target_names=class_names,
    digits=4,
    zero_division=0
)

print(report_text)


# Save text report
with open(
    os.path.join(
        OUTPUT_DIR,
        "step9_final_controlled_evaluation_report.txt"
    ),
    "w"
) as f:

    f.write(
        "STEP 9 — FINAL CONTROLLED MODEL EVALUATION\n"
    )

    f.write("=" * 90 + "\n\n")

    f.write(
        f"Checkpoint:\n{CHECKPOINT_FILE}\n\n"
    )

    f.write(
        f"Accuracy: {accuracy:.6f}\n"
    )

    f.write(
        f"Accuracy (%): {accuracy * 100:.2f}\n"
    )

    f.write(
        f"Macro Precision: {macro_precision:.6f}\n"
    )

    f.write(
        f"Macro Recall: {macro_recall:.6f}\n"
    )

    f.write(
        f"Macro F1: {macro_f1:.6f}\n"
    )

    f.write(
        f"Weighted Precision: {weighted_precision:.6f}\n"
    )

    f.write(
        f"Weighted Recall: {weighted_recall:.6f}\n"
    )

    f.write(
        f"Weighted F1: {weighted_f1:.6f}\n\n"
    )

    f.write(
        report_text
    )


# =============================================================================
# 22. CONFUSION MATRIX
# =============================================================================

print("\n[16] CONFUSION MATRIX")
print("-" * 90)

cm = confusion_matrix(
    true_labels,
    predictions,
    labels=list(range(len(class_names)))
)

cm_df = pd.DataFrame(
    cm,
    index=class_names,
    columns=class_names
)

print(cm_df.to_string())


cm_csv = os.path.join(
    OUTPUT_DIR,
    "step9_controlled_confusion_matrix.csv"
)

cm_df.to_csv(
    cm_csv
)

print(
    "\nSaved:",
    cm_csv
)


# =============================================================================
# 23. CLASS-WISE METRICS CSV
# =============================================================================

report_dict = classification_report(
    true_labels,
    predictions,
    labels=list(range(len(class_names))),
    target_names=class_names,
    output_dict=True,
    zero_division=0
)

class_metrics = []

for cls in class_names:

    row = report_dict[cls]

    class_metrics.append({

        "class": cls,

        "precision": row["precision"],

        "recall": row["recall"],

        "f1_score": row["f1-score"],

        "support": row["support"]
    })


class_metrics_df = pd.DataFrame(
    class_metrics
)

metrics_csv = os.path.join(
    OUTPUT_DIR,
    "step9_controlled_classwise_metrics.csv"
)

class_metrics_df.to_csv(
    metrics_csv,
    index=False
)

print(
    "Saved:",
    metrics_csv
)


# =============================================================================
# 24. SAVE ALL PREDICTIONS
# =============================================================================

print("\n[17] SAVING ALL PREDICTIONS")
print("-" * 90)

prediction_df = dataset_df.copy()

prediction_df["true_class"] = [
    index_to_label[i]
    for i in true_labels
]

prediction_df["predicted_class"] = [
    index_to_label[i]
    for i in predictions
]

prediction_df["correct"] = (
    true_labels == predictions
)

prediction_df["confidence"] = confidences

# Add probability for every class
for i, cls in index_to_label.items():

    prediction_df[
        f"prob_{cls}"
    ] = probabilities[:, i]


all_predictions_file = os.path.join(
    OUTPUT_DIR,
    "step9_controlled_all_640_predictions.csv"
)

prediction_df.to_csv(
    all_predictions_file,
    index=False
)

print(
    "Saved:",
    all_predictions_file
)


# =============================================================================
# 25. CORRECT / WRONG PREDICTIONS
# =============================================================================

correct_df = prediction_df[
    prediction_df["correct"] == True
].copy()

wrong_df = prediction_df[
    prediction_df["correct"] == False
].copy()


correct_file = os.path.join(
    OUTPUT_DIR,
    "step9_controlled_correct_predictions.csv"
)

wrong_file = os.path.join(
    OUTPUT_DIR,
    "step9_controlled_wrong_predictions.csv"
)

correct_df.to_csv(
    correct_file,
    index=False
)

wrong_df.to_csv(
    wrong_file,
    index=False
)

print(
    "Correct predictions:",
    len(correct_df)
)

print(
    "Wrong predictions:",
    len(wrong_df)
)

print(
    "Saved:",
    correct_file
)

print(
    "Saved:",
    wrong_file
)


# =============================================================================
# 26. CONFIDENCE ANALYSIS
# =============================================================================

print("\n[18] CONFIDENCE ANALYSIS")
print("-" * 90)

correct_mask = (
    predictions == true_labels
)

wrong_mask = ~correct_mask

mean_confidence = confidences.mean()

correct_confidence = (
    confidences[correct_mask].mean()
    if correct_mask.any()
    else 0.0
)

wrong_confidence = (
    confidences[wrong_mask].mean()
    if wrong_mask.any()
    else 0.0
)

print(
    f"Overall mean confidence : {mean_confidence:.4f}"
)

print(
    f"Correct mean confidence  : {correct_confidence:.4f}"
)

print(
    f"Wrong mean confidence    : {wrong_confidence:.4f}"
)

print(
    f"Minimum confidence      : {confidences.min():.4f}"
)

print(
    f"Maximum confidence      : {confidences.max():.4f}"
)


# =============================================================================
# 27. TEMPORAL ATTENTION ANALYSIS
# =============================================================================

print("\n[19] TEMPORAL ATTENTION")
print("-" * 90)

mean_attention = attention.mean(
    axis=0
)

print(
    "Mean temporal attention:"
)

for t, value in enumerate(
    mean_attention
):

    print(
        f"Timestep {t + 1:02d}: "
        f"{value:.6f}"
    )

print(
    "\nAttention sum:",
    mean_attention.sum()
)

attention_df = pd.DataFrame({

    "timestep": np.arange(
        1,
        11
    ),

    "mean_attention": mean_attention
})

attention_file = os.path.join(
    OUTPUT_DIR,
    "step9_controlled_temporal_attention.csv"
)

attention_df.to_csv(
    attention_file,
    index=False
)

print(
    "Saved:",
    attention_file
)


# =============================================================================
# 28. TOP MISCLASSIFICATION PAIRS
# =============================================================================

print("\n[20] TOP MISCLASSIFICATION PAIRS")
print("-" * 90)

wrong_pairs = pd.DataFrame({

    "true_class": [
        index_to_label[i]
        for i in true_labels[wrong_mask]
    ],

    "predicted_class": [
        index_to_label[i]
        for i in predictions[wrong_mask]
    ]
})

if len(wrong_pairs) > 0:

    pair_counts = (
        wrong_pairs
        .value_counts()
        .reset_index(
            name="count"
        )
    )

    print(
        pair_counts.head(20).to_string(
            index=False
        )
    )

else:

    pair_counts = pd.DataFrame(
        columns=[
            "true_class",
            "predicted_class",
            "count"
        ]
    )

pair_file = os.path.join(
    OUTPUT_DIR,
    "step9_controlled_top_misclassification_pairs.csv"
)

pair_counts.to_csv(
    pair_file,
    index=False
)

print(
    "\nSaved:",
    pair_file
)


# =============================================================================
# 29. TARGET CHECK
# =============================================================================

print("\n[21] 80% TARGET CHECK")
print("-" * 90)

if accuracy >= 0.80:

    print(
        "✓ FINAL EVALUATION IS ABOVE 80%"
    )

else:

    print(
        "⚠ FINAL 640-SAMPLE EVALUATION IS BELOW 80%"
    )

print(
    f"Final 640-sample accuracy: "
    f"{accuracy * 100:.2f}%"
)


# =============================================================================
# 30. IMPORTANT INTERPRETATION
# =============================================================================

print("\n[22] INTERPRETATION")
print("-" * 90)

print(
    "IMPORTANT:"
)

print(
    "This evaluation uses the EXACT Step 7 Controlled checkpoint:"
)

print(
    CHECKPOINT_FILE
)

print(
    "\nThis is different from the previously evaluated "
    "'step7L_improved_best.pth'."
)

print(
    "\nThe 80.47% Step 7 validation result remains "
    "the official held-out validation result."
)

print(
    "\nThis Step 9 run evaluates all 640 available samples "
    "and should NOT be directly compared with the 128-sample "
    "validation accuracy."
)


# =============================================================================
# 31. FINAL SUMMARY
# =============================================================================

correct_count = int(
    (predictions == true_labels).sum()
)

wrong_count = int(
    (predictions != true_labels).sum()
)

print("\n")
print("=" * 90)
print("STEP 9 — FINAL CONTROLLED MODEL EVALUATION COMPLETE")
print("=" * 90)

print(
    "\nCheckpoint:"
)

print(
    CHECKPOINT_FILE
)

print(
    f"\nFinal 640-sample Accuracy : "
    f"{accuracy * 100:.2f}%"
)

print(
    f"Macro F1                  : "
    f"{macro_f1:.4f}"
)

print(
    f"Weighted F1               : "
    f"{weighted_f1:.4f}"
)

print(
    f"Correct                   : "
    f"{correct_count} / 640"
)

print(
    f"Wrong                     : "
    f"{wrong_count} / 640"
)

print(
    "\nStep 7 held-out validation accuracy:"
)

print(
    "80.47%"
)

print(
    "\n✓ STEP 9 EVALUATION COMPLETE"
)

print(
    "\nOutput directory:"
)

print(
    OUTPUT_DIR
)

print("\nMain output files:")

print(
    "1.",
    os.path.join(
        OUTPUT_DIR,
        "step9_final_controlled_evaluation_report.txt"
    )
)

print(
    "2.",
    cm_csv
)

print(
    "3.",
    metrics_csv
)

print(
    "4.",
    all_predictions_file
)

print(
    "5.",
    wrong_file
)

print(
    "6.",
    attention_file
)

print(
    "7.",
    pair_file
)

print(
    "\n" + "=" * 90
)
print("DONE")
print("=" * 90)