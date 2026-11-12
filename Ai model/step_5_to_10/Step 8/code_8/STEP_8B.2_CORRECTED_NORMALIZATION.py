# =============================================================================
# STEP_8B.2 — FINAL TEMPORAL CROSS-ATTENTION EXTRACTION
# =============================================================================
#
# VERIFIED INPUTS
# ----------------
# Image embeddings       : 640 × 1792
# Satellite sequences    : 58 × 10 × 3
# Rectified mapping      : 640 rows
# Checkpoint             : step7L_improved_best.pth
#
# OUTPUT
# ----------------
# 1. 640 × 10 temporal attention CSV
# 2. Per-image prediction CSV
# 3. Field-wise temporal summary
# 4. Timestep summary
# 5. Attention heatmap
# 6. Mean temporal attention plot
# 7. Field-wise temporal attention plots
# 8. Final verification report
#
# =============================================================================

import os
import glob
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt


# =============================================================================
# 1. DRIVE
# =============================================================================

from google.colab import drive

drive.mount("/content/drive")

print("=" * 100)
print("STEP 8B — FINAL TEMPORAL CROSS-ATTENTION EXTRACTION")
print("=" * 100)


# =============================================================================
# 2. PATHS
# =============================================================================

PROJECT_ROOT = "/content/drive/MyDrive/final year project"

STEP5_ROOT = os.path.join(
    PROJECT_ROOT,
    "Real_world_test",
    "Step 5"
)

STEP7_ROOT = os.path.join(
    PROJECT_ROOT,
    "Real_world_test",
    "Step 7"
)

IMAGE_PATH = os.path.join(
    STEP7_ROOT,
    "step7_FINAL_image_embeddings_1792.npy"
)

SATELLITE_PATH = os.path.join(
    STEP5_ROOT,
    "bilstm_sequences.npy"
)

MAPPING_PATH = os.path.join(
    STEP7_ROOT,
    "step8B_final_rectified_640_mapping.csv"
)

# Automatically find verified checkpoint
checkpoint_candidates = glob.glob(
    os.path.join(
        STEP7_ROOT,
        "**",
        "step7L_improved_best.pth"
    ),
    recursive=True
)

if len(checkpoint_candidates) == 0:
    raise FileNotFoundError(
        "step7L_improved_best.pth not found."
    )

CHECKPOINT_PATH = checkpoint_candidates[0]


# =============================================================================
# 3. OUTPUT DIRECTORY
# =============================================================================

OUTPUT_DIR = os.path.join(
    STEP7_ROOT,
    "Step8B_Corrected_Normalization"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

print("\nOutput directory:")
print(OUTPUT_DIR)


# =============================================================================
# 4. OUTPUT FILES
# =============================================================================

ATTENTION_CSV = os.path.join(
    OUTPUT_DIR,
    "step8B_final_640x10_temporal_attention.csv"
)

PREDICTION_CSV = os.path.join(
    OUTPUT_DIR,
    "step8B_final_predictions_640.csv"
)

FIELD_SUMMARY_CSV = os.path.join(
    OUTPUT_DIR,
    "step8B_field_temporal_attention_summary.csv"
)

TIMESTEP_SUMMARY_CSV = os.path.join(
    OUTPUT_DIR,
    "step8B_timestep_attention_summary.csv"
)

IMAGE_SUMMARY_CSV = os.path.join(
    OUTPUT_DIR,
    "step8B_image_temporal_summary.csv"
)

HEATMAP_PNG = os.path.join(
    OUTPUT_DIR,
    "step8B_temporal_attention_heatmap_640x10.png"
)

MEAN_PLOT_PNG = os.path.join(
    OUTPUT_DIR,
    "step8B_mean_temporal_attention.png"
)

FIELD_PLOT_DIR = os.path.join(
    OUTPUT_DIR,
    "field_temporal_plots"
)

os.makedirs(
    FIELD_PLOT_DIR,
    exist_ok=True
)

REPORT_PATH = os.path.join(
    OUTPUT_DIR,
    "step8B_final_temporal_attention_report.txt"
)


# =============================================================================
# 5. REQUIRED FILE CHECK
# =============================================================================

print("\n[1] REQUIRED FILES")
print("-" * 100)

required_files = {
    "Image embeddings": IMAGE_PATH,
    "Satellite sequences": SATELLITE_PATH,
    "Rectified mapping": MAPPING_PATH,
    "Checkpoint": CHECKPOINT_PATH
}

for name, path in required_files.items():

    if os.path.exists(path):

        print(
            f"COMPLETE  {name}"
        )

        print(
            f"          {path}"
        )

    else:

        raise FileNotFoundError(
            f"{name} missing:\n{path}"
        )


# =============================================================================
# 6. LOAD DATA
# =============================================================================

print("\n[2] LOADING DATA")
print("-" * 100)

image_embeddings = np.load(
    IMAGE_PATH
).astype(np.float32)

satellite_sequences = np.load(
    SATELLITE_PATH
).astype(np.float32)

mapping = pd.read_csv(
    MAPPING_PATH
)

print(
    "Image embeddings:",
    image_embeddings.shape
)

print(
    "Satellite sequences:",
    satellite_sequences.shape
)

print(
    "Mapping:",
    mapping.shape
)


# =============================================================================
# 7. VALIDATE INPUTS
# =============================================================================

print("\n[3] INPUT VALIDATION")
print("-" * 100)

assert image_embeddings.shape == (
    640,
    1792
), image_embeddings.shape

assert satellite_sequences.shape == (
    58,
    10,
    3
), satellite_sequences.shape

assert len(mapping) == 640

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

print(
    "Image embeddings : 640 × 1792 COMPLETE"
)

print(
    "Satellite data   : 58 × 10 × 3 COMPLETE"
)

print(
    "Mapping          : 640 rows COMPLETE"
)

print(
    "NaN/Inf check    : COMPLETE"
)


# =============================================================================
# 8. SATELLITE INDEX
# =============================================================================

mapping[
    "satellite_embedding_index"
] = pd.to_numeric(
    mapping[
        "satellite_embedding_index"
    ],
    errors="raise"
).astype(int)

satellite_indices = mapping[
    "satellite_embedding_index"
].to_numpy()

assert satellite_indices.min() >= 0

assert satellite_indices.max() < 58

print(
    "Satellite index range:",
    satellite_indices.min(),
    "to",
    satellite_indices.max()
)


# =============================================================================
# 9. BUILD ALIGNED SATELLITE INPUT
# =============================================================================

print("\n[4] BUILDING ALIGNED SATELLITE INPUT")
print("-" * 100)

aligned_satellite = satellite_sequences[
    satellite_indices
]

assert aligned_satellite.shape == (
    640,
    10,
    3
)

print(
    "Aligned satellite shape:",
    aligned_satellite.shape
)

print(
    "640 image ↔ satellite sequence alignment COMPLETE"
)


# =============================================================================
# 10. DEVICE
# =============================================================================

print("\n[5] DEVICE")
print("-" * 100)

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print(
    "Device:",
    device
)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


# =============================================================================
# 11. EXACT VERIFIED MODEL
# =============================================================================

class Step7LImprovedActual(nn.Module):

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

        # Image projection
        self.image_projection = nn.Sequential(

            nn.Linear(
                image_dim,
                projection_dim
            ),

            nn.LayerNorm(
                projection_dim
            )
        )

        # 2-layer BiLSTM
        self.satellite_lstm = nn.LSTM(

            input_size=satellite_input_dim,

            hidden_size=lstm_hidden,

            num_layers=2,

            batch_first=True,

            bidirectional=True
        )

        # Satellite projection
        self.satellite_projection = nn.Sequential(

            nn.Linear(
                256,
                256
            ),

            nn.LayerNorm(
                256
            )
        )

        # Cross attention
        self.cross_attention = nn.MultiheadAttention(

            embed_dim=256,

            num_heads=num_heads,

            batch_first=True
        )

        # Attention normalization
        self.attention_norm = nn.LayerNorm(
            256
        )

        # Fusion
        self.fusion = nn.Sequential(

            nn.Linear(
                512,
                256
            ),

            nn.LayerNorm(
                256
            ),

            nn.ReLU(),

            nn.Dropout(
                0.4
            ),

            nn.Linear(
                256,
                128
            )
        )

        # Classifier
        self.classifier = nn.Linear(
            128,
            num_classes
        )


    def forward(
        self,
        image_features,
        satellite_sequence,
        return_attention=False
    ):

        # Image
        image_features = self.image_projection(
            image_features
        )

        # Satellite temporal sequence
        satellite_features, _ = self.satellite_lstm(
            satellite_sequence
        )

        # Satellite projection
        satellite_features = self.satellite_projection(
            satellite_features
        )

        # Image query
        query = image_features.unsqueeze(1)

        # Cross attention
        attended, attention_weights = self.cross_attention(

            query,

            satellite_features,

            satellite_features,

            need_weights=return_attention,

            average_attn_weights=True
        )

        attended = attended.squeeze(1)

        # Attention normalization
        attended = self.attention_norm(
            attended
        )

        # Image + attended satellite
        fusion_input = torch.cat(
            [
                image_features,
                attended
            ],
            dim=1
        )

        # Fusion
        fused = self.fusion(
            fusion_input
        )

        # Class prediction
        logits = self.classifier(
            fused
        )

        if return_attention:

            return (
                logits,
                attention_weights
            )

        return logits


# =============================================================================
# 12. LOAD CHECKPOINT
# =============================================================================

print("\n[6] LOADING VERIFIED CHECKPOINT")
print("-" * 100)

checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location=device,
    weights_only=False
)

state_dict = checkpoint[
    "model_state_dict"
]

# ============================================================
# CORRECTED SATELLITE NORMALIZATION
# Uses exact statistics saved in the trained checkpoint.
# ============================================================
satellite_mean = np.asarray(
    checkpoint["satellite_mean"],
    dtype=np.float32
)

satellite_std = np.asarray(
    checkpoint["satellite_std"],
    dtype=np.float32
)

assert satellite_mean.shape == (3,)
assert satellite_std.shape == (3,)
assert np.all(satellite_std > 0)

aligned_satellite = (
    aligned_satellite
    - satellite_mean.reshape(1, 1, 3)
) / satellite_std.reshape(1, 1, 3)

assert aligned_satellite.shape == (640, 10, 3)
assert np.isfinite(aligned_satellite).all()

print("\\nCORRECTED SATELLITE NORMALIZATION")
print("Mean:", satellite_mean)
print("Std :", satellite_std)
print("Shape:", aligned_satellite.shape)


print(
    "Checkpoint:",
    CHECKPOINT_PATH
)

print(
    "Epoch:",
    checkpoint.get(
        "epoch",
        "N/A"
    )
)

print(
    "Best validation accuracy:",
    checkpoint.get(
        "best_val_accuracy",
        "N/A"
    )
)

print(
    "Best validation F1:",
    checkpoint.get(
        "best_val_f1",
        "N/A"
    )
)


# =============================================================================
# 13. CREATE MODEL + LOAD
# =============================================================================

print("\n[7] LOADING MODEL")
print("-" * 100)

model = Step7LImprovedActual(
    image_dim=1792,
    satellite_input_dim=3,
    lstm_hidden=128,
    projection_dim=256,
    num_heads=8,
    num_classes=11
)

model.load_state_dict(
    state_dict,
    strict=True
)

model = model.to(
    device
)

model.eval()

print(
    "strict=True checkpoint loading COMPLETE"
)


# =============================================================================
# 14. CLASS NAMES
# =============================================================================

class_names = checkpoint.get(
    "class_names",
    None
)

if class_names is None:

    class_names = [
        f"class_{i}"
        for i in range(11)
    ]

else:

    class_names = list(
        class_names
    )

print(
    "\nClass names:"
)

for i, name in enumerate(
    class_names
):

    print(
        f"{i:2d} -> {name}"
    )


# =============================================================================
# 15. FULL 640-IMAGE TEMPORAL ATTENTION EXTRACTION
# =============================================================================

print("\n[8] EXTRACTING TEMPORAL ATTENTION")
print("-" * 100)

BATCH_SIZE = 32

all_logits = []

all_attention = []

total_images = len(
    image_embeddings
)

with torch.no_grad():

    for start in range(
        0,
        total_images,
        BATCH_SIZE
    ):

        end = min(
            start + BATCH_SIZE,
            total_images
        )

        batch_images = torch.from_numpy(
            image_embeddings[
                start:end
            ]
        ).float().to(device)

        batch_satellite = torch.from_numpy(
            aligned_satellite[
                start:end
            ]
        ).float().to(device)

        logits, attention = model(

            batch_images,

            batch_satellite,

            return_attention=True
        )

        all_logits.append(
            logits
            .detach()
            .cpu()
            .numpy()
        )

        all_attention.append(
            attention
            .detach()
            .cpu()
            .numpy()
        )

        print(
            f"Processed {end:4d}/{total_images}"
        )


# =============================================================================
# 16. COMBINE OUTPUTS
# =============================================================================

all_logits = np.concatenate(
    all_logits,
    axis=0
)

all_attention = np.concatenate(
    all_attention,
    axis=0
)


print("\nAttention extraction finished.")

print(
    "Logits shape:",
    all_logits.shape
)

print(
    "Attention raw shape:",
    all_attention.shape
)


# Expected:
# logits     = (640,11)
# attention  = (640,1,10)

assert all_logits.shape == (
    640,
    11
)

assert all_attention.shape == (
    640,
    1,
    10
)


# Remove query dimension
attention_matrix = all_attention[
    :,
    0,
    :
]


assert attention_matrix.shape == (
    640,
    10
)


# =============================================================================
# 17. NUMERICAL VALIDATION
# =============================================================================

print("\n[9] ATTENTION NUMERICAL VALIDATION")
print("-" * 100)

print(
    "NaN:",
    np.isnan(
        attention_matrix
    ).sum()
)

print(
    "Inf:",
    np.isinf(
        attention_matrix
    ).sum()
)

assert not np.isnan(
    attention_matrix
).any()

assert not np.isinf(
    attention_matrix
).any()


# =============================================================================
# 18. ATTENTION SUM
# =============================================================================

attention_sums = attention_matrix.sum(
    axis=1
)

print(
    "Minimum row sum:",
    attention_sums.min()
)

print(
    "Maximum row sum:",
    attention_sums.max()
)

assert np.allclose(
    attention_sums,
    1.0,
    atol=1e-5
)

print(
    "All 640 attention rows sum to 1 COMPLETE"
)


# =============================================================================
# 19. PREDICTIONS
# =============================================================================

predicted_class_indices = np.argmax(
    all_logits,
    axis=1
)

predicted_classes = [
    class_names[i]
    for i in predicted_class_indices
]

probabilities = torch.softmax(
    torch.from_numpy(
        all_logits
    ),
    dim=1
).numpy()

prediction_confidence = probabilities.max(
    axis=1
)


# =============================================================================
# 20. TEMPORAL METRICS
# =============================================================================

print("\n[10] TEMPORAL METRICS")
print("-" * 100)

# Most attended timestep
dominant_timestep = np.argmax(
    attention_matrix,
    axis=1
)

# Maximum attention value
max_attention = np.max(
    attention_matrix,
    axis=1
)

# Weighted temporal position
timesteps = np.arange(
    1,
    11
)

weighted_temporal_position = (
    attention_matrix * timesteps
).sum(
    axis=1
)

# Entropy
epsilon = 1e-12

attention_entropy = -np.sum(
    attention_matrix *
    np.log(
        attention_matrix + epsilon
    ),
    axis=1
)

# Normalized entropy
attention_entropy_normalized = (
    attention_entropy /
    np.log(10)
)


# =============================================================================
# 21. COMPLETE IMAGE SUMMARY
# =============================================================================

print("\n[11] BUILDING IMAGE-LEVEL SUMMARY")
print("-" * 100)

image_summary = mapping.copy()

image_summary[
    "predicted_class_index"
] = predicted_class_indices

image_summary[
    "predicted_class"
] = predicted_classes

image_summary[
    "prediction_confidence"
] = prediction_confidence

image_summary[
    "dominant_timestep"
] = dominant_timestep + 1

image_summary[
    "maximum_attention"
] = max_attention

image_summary[
    "weighted_temporal_position"
] = weighted_temporal_position

image_summary[
    "attention_entropy"
] = attention_entropy

image_summary[
    "attention_entropy_normalized"
] = attention_entropy_normalized


# Add each timestep
for t in range(10):

    image_summary[
        f"attention_t{t+1}"
    ] = attention_matrix[
        :,
        t
    ]


# =============================================================================
# 22. SAVE IMAGE SUMMARY
# =============================================================================

image_summary.to_csv(
    IMAGE_SUMMARY_CSV,
    index=False
)

print(
    "Saved:",
    IMAGE_SUMMARY_CSV
)


# =============================================================================
# 23. 640 × 10 ATTENTION CSV
# =============================================================================

print("\n[12] BUILDING 640 × 10 ATTENTION TABLE")
print("-" * 100)

attention_table = pd.DataFrame()

attention_table[
    "image_index"
] = np.arange(
    640
)

attention_table[
    "image_name"
] = mapping[
    "image_name"
].values

attention_table[
    "image_path"
] = mapping[
    "image_path"
].values

attention_table[
    "nearest_satellite_field"
] = mapping[
    "nearest_satellite_field"
].values

attention_table[
    "satellite_embedding_index"
] = mapping[
    "satellite_embedding_index"
].values

attention_table[
    "predicted_class"
] = predicted_classes

attention_table[
    "prediction_confidence"
] = prediction_confidence

attention_table[
    "dominant_timestep"
] = dominant_timestep + 1

attention_table[
    "maximum_attention"
] = max_attention

attention_table[
    "weighted_temporal_position"
] = weighted_temporal_position

attention_table[
    "attention_entropy"
] = attention_entropy


for t in range(10):

    attention_table[
        f"timestep_{t+1}_attention"
    ] = attention_matrix[
        :,
        t
    ]


attention_table.to_csv(
    ATTENTION_CSV,
    index=False
)

print(
    "Saved:",
    ATTENTION_CSV
)


# =============================================================================
# 24. PREDICTION CSV
# =============================================================================

prediction_table = mapping[
    [
        "image_name",
        "image_path",
        "nearest_satellite_field",
        "satellite_embedding_index"
    ]
].copy()

prediction_table[
    "predicted_class_index"
] = predicted_class_indices

prediction_table[
    "predicted_class"
] = predicted_classes

prediction_table[
    "prediction_confidence"
] = prediction_confidence

prediction_table[
    "dominant_timestep"
] = dominant_timestep + 1

prediction_table[
    "maximum_attention"
] = max_attention

prediction_table[
    "weighted_temporal_position"
] = weighted_temporal_position

prediction_table[
    "attention_entropy"
] = attention_entropy


prediction_table.to_csv(
    PREDICTION_CSV,
    index=False
)

print(
    "Saved:",
    PREDICTION_CSV
)


# =============================================================================
# 25. TIMESTEP SUMMARY
# =============================================================================

print("\n[13] TIMESTEP SUMMARY")
print("-" * 100)

timestep_summary = pd.DataFrame({

    "timestep": np.arange(
        1,
        11
    ),

    "mean_attention": attention_matrix.mean(
        axis=0
    ),

    "std_attention": attention_matrix.std(
        axis=0
    ),

    "median_attention": np.median(
        attention_matrix,
        axis=0
    ),

    "minimum_attention": attention_matrix.min(
        axis=0
    ),

    "maximum_attention": attention_matrix.max(
        axis=0
    ),

    "dominant_count": [
        np.sum(
            dominant_timestep == t
        )
        for t in range(10)
    ]
})

timestep_summary[
    "dominant_percentage"
] = (
    timestep_summary[
        "dominant_count"
    ] / 640 * 100
)

timestep_summary.to_csv(
    TIMESTEP_SUMMARY_CSV,
    index=False
)

print(
    timestep_summary.to_string(
        index=False
    )
)

print(
    "\nSaved:",
    TIMESTEP_SUMMARY_CSV
)


# =============================================================================
# 26. FIELD-WISE SUMMARY
# =============================================================================

print("\n[14] FIELD-WISE TEMPORAL SUMMARY")
print("-" * 100)

field_rows = []

for field, group in image_summary.groupby(
    "nearest_satellite_field"
):

    indices = group.index.to_numpy()

    field_attention = attention_matrix[
        indices
    ]

    field_mean_attention = field_attention.mean(
        axis=0
    )

    dominant_counts = np.bincount(
        dominant_timestep[
            indices
        ],
        minlength=10
    )

    dominant_field_timestep = (
        np.argmax(
            dominant_counts
        ) + 1
    )

    row = {

        "satellite_field": field,

        "image_count": len(group),

        "mean_confidence":
            group[
                "prediction_confidence"
            ].mean(),

        "mean_attention_entropy":
            group[
                "attention_entropy"
            ].mean(),

        "dominant_timestep":
            dominant_field_timestep
    }

    for t in range(10):

        row[
            f"mean_attention_t{t+1}"
        ] = field_mean_attention[
            t
        ]

    field_rows.append(
        row
    )


field_summary = pd.DataFrame(
    field_rows
)

field_summary = field_summary.sort_values(
    "image_count",
    ascending=False
)

field_summary.to_csv(
    FIELD_SUMMARY_CSV,
    index=False
)

print(
    field_summary.to_string(
        index=False
    )
)

print(
    "\nSaved:",
    FIELD_SUMMARY_CSV
)


# =============================================================================
# 27. MEAN TEMPORAL ATTENTION PLOT
# =============================================================================

print("\n[15] CREATING MEAN TEMPORAL ATTENTION PLOT")
print("-" * 100)

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    timestep_summary[
        "timestep"
    ],
    timestep_summary[
        "mean_attention"
    ],
    marker="o"
)

plt.xticks(
    range(1, 11)
)

plt.xlabel(
    "Satellite Temporal Timestep"
)

plt.ylabel(
    "Mean Cross-Attention Weight"
)

plt.title(
    "Mean Temporal Cross-Attention Across 640 Images"
)

plt.grid(
    True,
    alpha=0.3
)

plt.tight_layout()

plt.savefig(
    MEAN_PLOT_PNG,
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print(
    "Saved:",
    MEAN_PLOT_PNG
)


# =============================================================================
# 28. HEATMAP
# =============================================================================

print("\n[16] CREATING ATTENTION HEATMAP")
print("-" * 100)

plt.figure(
    figsize=(12, 12)
)

plt.imshow(
    attention_matrix,
    aspect="auto",
    interpolation="nearest"
)

plt.colorbar(
    label="Attention Weight"
)

plt.xlabel(
    "Satellite Temporal Timestep"
)

plt.ylabel(
    "Image Index"
)

plt.xticks(
    range(10),
    [
        f"T{i}"
        for i in range(1, 11)
    ]
)

plt.title(
    "Temporal Cross-Attention Heatmap — 640 Images × 10 Timesteps"
)

plt.tight_layout()

plt.savefig(
    HEATMAP_PNG,
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print(
    "Saved:",
    HEATMAP_PNG
)


# =============================================================================
# 29. FIELD-WISE PLOTS
# =============================================================================

print("\n[17] CREATING FIELD-WISE TEMPORAL PLOTS")
print("-" * 100)

for _, row in field_summary.iterrows():

    field = row[
        "satellite_field"
    ]

    values = [
        row[
            f"mean_attention_t{t}"
        ]
        for t in range(1, 11)
    ]

    safe_field = (
        str(field)
        .replace(
            "/",
            "_"
        )
        .replace(
            "\\",
            "_"
        )
        .replace(
            " ",
            "_"
        )
    )

    output_path = os.path.join(
        FIELD_PLOT_DIR,
        f"{safe_field}_temporal_attention.png"
    )

    plt.figure(
        figsize=(9, 5)
    )

    plt.plot(
        range(1, 11),
        values,
        marker="o"
    )

    plt.xticks(
        range(1, 11)
    )

    plt.xlabel(
        "Satellite Temporal Timestep"
    )

    plt.ylabel(
        "Mean Attention Weight"
    )

    plt.title(
        f"Temporal Attention — {field}"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


print(
    "Field-wise plots created:",
    len(field_summary)
)


# =============================================================================
# 30. FINAL VALIDATION
# =============================================================================

print("\n[18] FINAL VALIDATION")
print("-" * 100)

assert len(image_summary) == 640

assert len(attention_table) == 640

assert len(prediction_table) == 640

assert attention_matrix.shape == (
    640,
    10
)

assert np.allclose(
    attention_matrix.sum(
        axis=1
    ),
    1.0,
    atol=1e-5
)

assert np.isfinite(
    attention_matrix
).all()

assert np.isfinite(
    prediction_confidence
).all()

print(
    "640 image records             : COMPLETE"
)

print(
    "10 temporal attention values  : COMPLETE"
)

print(
    "Predictions                   : COMPLETE"
)

print(
    "Attention normalization       : COMPLETE"
)

print(
    "Field summaries               : COMPLETE"
)

print(
    "Plots                         : COMPLETE"
)


# =============================================================================
# 31. FINAL REPORT
# =============================================================================

report = f"""
================================================================================
STEP 8B — FINAL TEMPORAL CROSS-ATTENTION EXTRACTION REPORT
================================================================================

INPUTS
--------------------------------------------------------------------------------
Image embeddings             : {image_embeddings.shape}
Satellite sequences          : {satellite_sequences.shape}
Final mapping                : {mapping.shape}

MODEL
--------------------------------------------------------------------------------
Checkpoint                   : {CHECKPOINT_PATH}
Epoch                        : {checkpoint.get("epoch", "N/A")}
Best validation accuracy     : {checkpoint.get("best_val_accuracy", "N/A")}
Best validation F1           : {checkpoint.get("best_val_f1", "N/A")}

ARCHITECTURE
--------------------------------------------------------------------------------
Image dimension              : 1792
Image projection             : 256
Satellite input              : 3
Satellite timesteps          : 10
BiLSTM layers                : 2
BiLSTM hidden                : 128
BiLSTM output                : 256
Satellite projection         : 256
Cross-attention heads        : 8
Fusion input                 : 512
Fusion hidden                : 256
Fusion output                : 128
Classes                      : 11

EXTRACTION
--------------------------------------------------------------------------------
Images processed             : 640
Attention matrix             : {attention_matrix.shape}
Logits matrix                : {all_logits.shape}
Attention NaN                : {np.isnan(attention_matrix).sum()}
Attention Inf                : {np.isinf(attention_matrix).sum()}
Minimum attention row sum    : {attention_sums.min()}
Maximum attention row sum    : {attention_sums.max()}

OUTPUTS
--------------------------------------------------------------------------------
Attention CSV               : {ATTENTION_CSV}
Prediction CSV               : {PREDICTION_CSV}
Image summary CSV            : {IMAGE_SUMMARY_CSV}
Field summary CSV            : {FIELD_SUMMARY_CSV}
Timestep summary CSV         : {TIMESTEP_SUMMARY_CSV}
Heatmap                      : {HEATMAP_PNG}
Mean temporal plot           : {MEAN_PLOT_PNG}
Field plots                  : {FIELD_PLOT_DIR}

STATUS
--------------------------------------------------------------------------------
Model loading               : COMPLETE
640-image inference         : COMPLETE
Temporal attention          : COMPLETE
Prediction extraction       : COMPLETE
Field-wise analysis         : COMPLETE
Visualization               : COMPLETE
Final validation            : COMPLETE

IMPORTANT INTERPRETATION
--------------------------------------------------------------------------------
Attention weights indicate which satellite timesteps the trained model
attended to during prediction. They should not by themselves be interpreted
as proof of disease onset at a particular timestep.

================================================================================
"""


with open(
    REPORT_PATH,
    "w"
) as f:

    f.write(
        report
    )


# =============================================================================
# 32. FINAL RESULT
# =============================================================================

print("\n")
print("=" * 100)
print("STEP 8B — FINAL TEMPORAL ATTENTION EXTRACTION COMPLETE")
print("=" * 100)

print(
    "Images processed:",
    len(image_summary)
)

print(
    "Attention matrix:",
    attention_matrix.shape
)

print(
    "Prediction matrix:",
    all_logits.shape
)

print(
    "Number of satellite fields represented:",
    mapping[
        "nearest_satellite_field"
    ].nunique()
)

print(
    "\nMAIN OUTPUT:"
)

print(
    ATTENTION_CSV
)

print(
    "\nSTATUS: STEP 8B COMPLETE"
)

print("=" * 100)