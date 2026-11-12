# =============================================================================
# STEP_8B.1 — FINAL CHECKPOINT + MAPPING COMPATIBILITY
# ACTUAL STEP 7L IMPROVED ARCHITECTURE
# =============================================================================

import os
import glob
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from google.colab import drive

# =============================================================================
# 1. DRIVE
# =============================================================================

drive.mount("/content/drive")

print("=" * 100)
print("STEP 8B — FINAL CHECKPOINT + MAPPING COMPATIBILITY")
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
    "step7_FINAL_image_field_satellite_mapping.csv"
)


# =============================================================================
# 3. AUTOMATIC CHECKPOINT SEARCH
# =============================================================================

print("\n[1] SEARCHING FOR CHECKPOINT")
print("-" * 100)

pth_files = glob.glob(
    os.path.join(
        STEP7_ROOT,
        "**",
        "*.pth"
    ),
    recursive=True
)

candidates = [
    p for p in pth_files
    if "step7l_improved_best" in
    os.path.basename(p).lower()
]

if len(candidates) == 0:

    print("Target checkpoint not found.")

    print("\nAvailable Step 7 checkpoints:")

    for p in pth_files:
        print(p)

    raise FileNotFoundError(
        "step7L_improved_best.pth not found."
    )


CHECKPOINT_PATH = candidates[0]

print(
    "Checkpoint found:"
)

print(
    CHECKPOINT_PATH
)


# =============================================================================
# 4. FILE CHECK
# =============================================================================

print("\n[2] REQUIRED FILES")
print("-" * 100)

required = {
    "Image embeddings": IMAGE_PATH,
    "Satellite sequences": SATELLITE_PATH,
    "Mapping": MAPPING_PATH,
    "Checkpoint": CHECKPOINT_PATH
}

for name, path in required.items():

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"{name} missing:\n{path}"
        )

    print(
        f"COMPLETE  {name}"
    )

    print(
        f"          {path}"
    )


# =============================================================================
# 5. LOAD DATA
# =============================================================================

print("\n[3] LOADING DATA")
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
    "Image embeddings   :",
    image_embeddings.shape
)

print(
    "Satellite sequences:",
    satellite_sequences.shape
)

print(
    "Mapping            :",
    mapping.shape
)


# =============================================================================
# 6. NUMERICAL CHECK
# =============================================================================

print("\n[4] NUMERICAL VALIDATION")
print("-" * 100)

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
    "Image embeddings NaN/Inf : 0"
)

print(
    "Satellite NaN/Inf        : 0"
)


# =============================================================================
# 7. SHAPE CHECK
# =============================================================================

print("\n[5] SHAPE VALIDATION")
print("-" * 100)

assert image_embeddings.shape == (
    640,
    1792
)

assert satellite_sequences.shape == (
    58,
    10,
    3
)

print(
    "Image embeddings : (640, 1792) COMPLETE"
)

print(
    "Satellite data   : (58, 10, 3) COMPLETE"
)


# =============================================================================
# 8. MAPPING CHECK
# =============================================================================

print("\n[6] MAPPING VALIDATION")
print("-" * 100)

mapping[
    "satellite_embedding_index"
] = pd.to_numeric(
    mapping[
        "satellite_embedding_index"
    ],
    errors="coerce"
)

valid_mask = (
    mapping[
        "satellite_embedding_index"
    ].notna()
    &
    (
        mapping[
            "satellite_embedding_index"
        ] >= 0
    )
    &
    (
        mapping[
            "satellite_embedding_index"
        ] < 58
    )
)

mapping = mapping.loc[
    valid_mask
].copy()

mapping.reset_index(
    drop=True,
    inplace=True
)

print(
    "Valid mapping rows:",
    len(mapping)
)


# =============================================================================
# 9. REMOVE DUPLICATE IMAGE NAMES
# =============================================================================

print("\n[7] DUPLICATE IMAGE RECTIFICATION")
print("-" * 100)

duplicates = mapping[
    mapping["image_name"].duplicated(
        keep=False
    )
]

print(
    "Duplicate rows detected:",
    len(duplicates)
)

if len(duplicates) > 0:

    print(
        "\nDuplicate entries:"
    )

    print(
        duplicates[
            [
                "image_name",
                "image_path",
                "satellite_embedding_index",
                "nearest_satellite_field"
            ]
        ].to_string(index=False)
    )

    mapping = mapping.drop_duplicates(
        subset=["image_name"],
        keep="first"
    ).reset_index(
        drop=True
    )

print(
    "Final mapping rows:",
    len(mapping)
)


# =============================================================================
# 10. FINAL 640 ALIGNMENT
# =============================================================================

print("\n[8] FINAL 640 ↔ 640 ALIGNMENT")
print("-" * 100)

if len(mapping) != 640:

    raise RuntimeError(
        f"Expected 640 mapping rows, found {len(mapping)}."
    )

print(
    "Image embeddings : 640"
)

print(
    "Mapping rows      : 640"
)

print(
    "640 ↔ 640 ALIGNMENT COMPLETE"
)


# =============================================================================
# 11. SATELLITE INDEX
# =============================================================================

satellite_indices = (
    mapping[
        "satellite_embedding_index"
    ]
    .astype(int)
    .to_numpy()
)

print(
    "\nSatellite index range:",
    satellite_indices.min(),
    "to",
    satellite_indices.max()
)

assert satellite_indices.min() >= 0
assert satellite_indices.max() < 58


# =============================================================================
# 12. ALIGNED SATELLITE DATA
# =============================================================================

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


# =============================================================================
# 13. DEVICE
# =============================================================================

print("\n[9] DEVICE")
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
# 14. LOAD CHECKPOINT
# =============================================================================

print("\n[10] LOADING CHECKPOINT")
print("-" * 100)

checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location=device,
    weights_only=False
)

state_dict = checkpoint[
    "model_state_dict"
]

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

print(
    "Best validation loss:",
    checkpoint.get(
        "best_val_loss",
        "N/A"
    )
)

print(
    "Classes:",
    checkpoint.get(
        "num_classes",
        "N/A"
    )
)


# =============================================================================
# 15. PRINT ACTUAL ARCHITECTURE
# =============================================================================

print("\n[11] ACTUAL CHECKPOINT ARCHITECTURE")
print("-" * 100)

for key, value in state_dict.items():

    print(
        f"{key:55s} {tuple(value.shape)}"
    )


# =============================================================================
# 16. ACTUAL STEP 7L IMPROVED MODEL
# =============================================================================
#
# Based directly on the checkpoint state_dict:
#
# image_projection
# satellite_lstm
# satellite_projection
# cross_attention
# attention_norm
# fusion
# classifier
#
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


        # ---------------------------------------------------------
        # IMAGE PROJECTION
        # ---------------------------------------------------------

        self.image_projection = nn.Sequential(

            nn.Linear(
                image_dim,
                projection_dim
            ),

            nn.LayerNorm(
                projection_dim
            )
        )


        # ---------------------------------------------------------
        # SATELLITE BiLSTM
        # ---------------------------------------------------------

        self.satellite_lstm = nn.LSTM(

            input_size=satellite_input_dim,

            hidden_size=lstm_hidden,

            num_layers=2,

            batch_first=True,

            bidirectional=True
        )


        # ---------------------------------------------------------
        # SATELLITE PROJECTION
        # ---------------------------------------------------------

        self.satellite_projection = nn.Sequential(

            nn.Linear(
                256,
                256
            ),

            nn.LayerNorm(
                256
            )
        )


        # ---------------------------------------------------------
        # CROSS ATTENTION
        # ---------------------------------------------------------

        self.cross_attention = nn.MultiheadAttention(

            embed_dim=256,

            num_heads=num_heads,

            batch_first=True
        )


        # ---------------------------------------------------------
        # ATTENTION NORMALIZATION
        # ---------------------------------------------------------

        self.attention_norm = nn.LayerNorm(
            256
        )


        # ---------------------------------------------------------
        # FUSION
        #
        # We construct this from checkpoint keys.
        #
        # fusion.0 -> Linear
        # fusion.1 -> normalization
        # fusion.4 -> final linear
        #
        # ---------------------------------------------------------

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


        # ---------------------------------------------------------
        # CLASSIFIER
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # IMAGE
        # ---------------------------------------------------------

        image_features = self.image_projection(
            image_features
        )


        # ---------------------------------------------------------
        # SATELLITE
        # ---------------------------------------------------------

        satellite_features, _ = self.satellite_lstm(
            satellite_sequence
        )


        # ---------------------------------------------------------
        # SATELLITE PROJECTION
        # ---------------------------------------------------------

        satellite_features = self.satellite_projection(
            satellite_features
        )


        # ---------------------------------------------------------
        # IMAGE QUERY
        # ---------------------------------------------------------

        query = image_features.unsqueeze(1)


        # ---------------------------------------------------------
        # CROSS ATTENTION
        # ---------------------------------------------------------

        attended, attention_weights = self.cross_attention(

            query,

            satellite_features,

            satellite_features,

            need_weights=return_attention,

            average_attn_weights=True
        )


        attended = attended.squeeze(1)


        # ---------------------------------------------------------
        # ATTENTION NORMALIZATION
        # ---------------------------------------------------------

        attended = self.attention_norm(
            attended
        )


        # ---------------------------------------------------------
        # CONCATENATION
        # ---------------------------------------------------------

        fusion_input = torch.cat(
            [
                image_features,
                attended
            ],
            dim=1
        )


        # ---------------------------------------------------------
        # FUSION
        # ---------------------------------------------------------

        fused = self.fusion(
            fusion_input
        )


        # ---------------------------------------------------------
        # CLASSIFIER
        # ---------------------------------------------------------

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
# 17. CREATE MODEL
# =============================================================================

print("\n[12] CREATING ACTUAL MODEL")
print("-" * 100)

model = Step7LImprovedActual(
    image_dim=1792,
    satellite_input_dim=3,
    lstm_hidden=128,
    projection_dim=256,
    num_heads=8,
    num_classes=11
)


# =============================================================================
# 18. LOAD STATE DICT
# =============================================================================

print("\n[13] LOADING CHECKPOINT WEIGHTS")
print("-" * 100)

model.load_state_dict(
    state_dict,
    strict=True
)

print(
    "strict=True checkpoint loading COMPLETE"
)


model = model.to(
    device
)

model.eval()


# =============================================================================
# 19. FORWARD TEST
# =============================================================================

print("\n[14] FORWARD PASS TEST")
print("-" * 100)

TEST_BATCH = 16

test_image = torch.from_numpy(
    image_embeddings[
        :TEST_BATCH
    ]
).float().to(device)

test_satellite = torch.from_numpy(
    aligned_satellite[
        :TEST_BATCH
    ]
).float().to(device)


with torch.no_grad():

    logits, attention = model(

        test_image,

        test_satellite,

        return_attention=True
    )


print(
    "Image input:",
    tuple(
        test_image.shape
    )
)

print(
    "Satellite input:",
    tuple(
        test_satellite.shape
    )
)

print(
    "Logits:",
    tuple(
        logits.shape
    )
)

print(
    "Attention:",
    tuple(
        attention.shape
    )
)


# =============================================================================
# 20. OUTPUT VALIDATION
# =============================================================================

print("\n[15] OUTPUT VALIDATION")
print("-" * 100)

logits_np = (
    logits
    .detach()
    .cpu()
    .numpy()
)

attention_np = (
    attention
    .detach()
    .cpu()
    .numpy()
)


print(
    "Logits NaN:",
    np.isnan(logits_np).sum()
)

print(
    "Logits Inf:",
    np.isinf(logits_np).sum()
)

print(
    "Attention NaN:",
    np.isnan(attention_np).sum()
)

print(
    "Attention Inf:",
    np.isinf(attention_np).sum()
)


assert not np.isnan(
    logits_np
).any()

assert not np.isinf(
    logits_np
).any()

assert not np.isnan(
    attention_np
).any()

assert not np.isinf(
    attention_np
).any()


# =============================================================================
# 21. ATTENTION VALIDATION
# =============================================================================

print("\n[16] ATTENTION VALIDATION")
print("-" * 100)

print(
    "Attention shape:",
    attention_np.shape
)

attention_sum = attention_np.sum(
    axis=-1
)

print(
    "Minimum attention sum:",
    attention_sum.min()
)

print(
    "Maximum attention sum:",
    attention_sum.max()
)


assert np.allclose(
    attention_sum,
    1.0,
    atol=1e-5
)

print(
    "Attention weights normalization COMPLETE"
)


# =============================================================================
# 22. SAVE RECTIFIED MAPPING
# =============================================================================

OUTPUT_MAPPING = os.path.join(
    STEP7_ROOT,
    "step8B_final_rectified_640_mapping.csv"
)

mapping.to_csv(
    OUTPUT_MAPPING,
    index=False
)

print(
    "\nSaved rectified mapping:"
)

print(
    OUTPUT_MAPPING
)


# =============================================================================
# 23. SAVE REPORT
# =============================================================================

OUTPUT_REPORT = os.path.join(
    STEP7_ROOT,
    "step8B_final_compatibility_report.txt"
)

report = f"""
================================================================================
STEP 8B — FINAL COMPATIBILITY REPORT
================================================================================

DATA
--------------------------------------------------------------------------------
Image embeddings        : {image_embeddings.shape}
Satellite sequences     : {satellite_sequences.shape}
Final mapping           : {mapping.shape}

CHECKPOINT
--------------------------------------------------------------------------------
Path                    : {CHECKPOINT_PATH}
Epoch                   : {checkpoint.get("epoch", "N/A")}
Best validation accuracy: {checkpoint.get("best_val_accuracy", "N/A")}
Best validation F1      : {checkpoint.get("best_val_f1", "N/A")}
Best validation loss    : {checkpoint.get("best_val_loss", "N/A")}
Classes                 : {checkpoint.get("num_classes", "N/A")}

ARCHITECTURE
--------------------------------------------------------------------------------
Image input             : 1792
Image projection        : 256
Satellite input         : 3
Satellite timesteps     : 10
BiLSTM                  : 2-layer bidirectional
BiLSTM hidden           : 128
BiLSTM output           : 256
Satellite projection    : 256
Cross attention         : 8 heads
Attention dimension     : 256
Fusion input            : 512
Fusion output           : 128
Classifier              : 128 -> 11

ALIGNMENT
--------------------------------------------------------------------------------
Images                  : 640
Mapping rows             : 640
Satellite sequences      : 58
Minimum satellite index  : {satellite_indices.min()}
Maximum satellite index  : {satellite_indices.max()}

FORWARD TEST
--------------------------------------------------------------------------------
Batch                   : {TEST_BATCH}
Logits shape             : {tuple(logits.shape)}
Attention shape          : {tuple(attention.shape)}

STATUS
--------------------------------------------------------------------------------
File validation          : COMPLETE
Numerical validation     : COMPLETE
Mapping rectification    : COMPLETE
640 ↔ 640 alignment      : COMPLETE
Checkpoint discovery     : COMPLETE
Checkpoint loading       : COMPLETE
Forward pass             : COMPLETE
Attention validation     : COMPLETE

NEXT STEP
--------------------------------------------------------------------------------
STEP 8B TEMPORAL ATTENTION EXTRACTION
================================================================================
"""

with open(
    OUTPUT_REPORT,
    "w"
) as f:

    f.write(
        report
    )


print(
    "Report saved:"
)

print(
    OUTPUT_REPORT
)


# =============================================================================
# 24. FINAL STATUS
# =============================================================================

print("\n")
print("=" * 100)
print("STEP 8B — FINAL STATUS")
print("=" * 100)

print(
    "Checkpoint:",
    os.path.basename(
        CHECKPOINT_PATH
    )
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
    "Final mapping:",
    mapping.shape
)

print(
    "Logits:",
    tuple(
        logits.shape
    )
)

print(
    "Attention:",
    tuple(
        attention.shape
    )
)

print(
    "\nSTATUS: STEP 8B COMPATIBILITY VERIFICATION COMPLETE"
)

print("=" * 100)