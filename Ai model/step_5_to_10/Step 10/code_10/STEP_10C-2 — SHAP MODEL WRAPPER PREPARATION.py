
# ============================================================
# STEP 10C-2 — SHAP MODEL WRAPPER PREPARATION
# CORRECTED VERSION
# ============================================================

import ast
import inspect
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from pathlib import Path

print("=" * 70)
print("STEP 10C-2 — SHAP MODEL WRAPPER PREPARATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. CORRECT FILE PATHS
# ------------------------------------------------------------

BASE = Path("/content/drive/MyDrive/final year project")

CHECKPOINT_PATH = (
    BASE / "AI_model/step_5_to_9/Step 7/models_7/"
    "Step7L_Temporal_CrossAttention_m_1/"
    "step7L_controlled_best.pth"
)

SOURCE_PATH = (
    BASE / "AI_model/step_5_to_9/Step 7/code_7/"
    "STEP_7k — TEMPORAL CROSS-ATTENTION MULTIMODAL TRAINING_Improved.py"
)

BACKGROUND_PATH = (
    BASE / "AI_model/step_5_to_9/Step 8/SHAP_Results/"
    "shap_satellite_background.npy"
)

# Corrected paths based on your file search.
EMBEDDINGS_PATH = (
    BASE / "AI_model/step_5_to_9/Step 7/models_7/"
    "step7_FINAL_image_embeddings_1792.npy"
)

DATASET_PATH = (
    BASE / "AI_model/step_5_to_9/Step 7/text_and_csv_files_7/"
    "step7I_final_11class_multimodal_dataset.csv"
)

MAPPING_PATH = (
    BASE / "AI_model/step_5_to_9/Step 7/"
    "step7_verified_field_embedding_mapping.csv"
)

SATELLITE_PATH = (
    BASE / "AI_model/step_5_to_9/Step 5/models_5/"
    "bilstm_sequences.npy"
)

required_paths = {
    "Checkpoint": CHECKPOINT_PATH,
    "Model source": SOURCE_PATH,
    "SHAP background": BACKGROUND_PATH,
    "Image embeddings": EMBEDDINGS_PATH,
    "Dataset CSV": DATASET_PATH,
    "Field mapping": MAPPING_PATH,
    "Satellite sequences": SATELLITE_PATH,
}

print("\n[1/8] Checking required files...")

for name, path in required_paths.items():
    print(f"{name}: {path.is_file()}")

missing = [
    name for name, path in required_paths.items()
    if not path.is_file()
]

if missing:
    raise FileNotFoundError(
        "Missing required files: " + ", ".join(missing)
    )

# ------------------------------------------------------------
# 2. LOAD CHECKPOINT AND DATA
# ------------------------------------------------------------

print("\n[2/8] Loading checkpoint and data...")

checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location="cpu",
    weights_only=False
)

if "model_state_dict" not in checkpoint:
    raise KeyError("Checkpoint has no model_state_dict.")

image_embeddings = np.load(
    EMBEDDINGS_PATH,
    allow_pickle=False
)

satellite_sequences = np.load(
    SATELLITE_PATH,
    allow_pickle=False
)

background_raw_np = np.load(
    BACKGROUND_PATH,
    allow_pickle=False
)

dataset = pd.read_csv(DATASET_PATH)
field_mapping = pd.read_csv(MAPPING_PATH)

print("Image embeddings:", image_embeddings.shape)
print("Satellite sequences:", satellite_sequences.shape)
print("Background:", background_raw_np.shape)
print("Dataset:", dataset.shape)
print("Field mapping:", field_mapping.shape)

# ------------------------------------------------------------
# 3. VALIDATE SHAPES AND REQUIRED COLUMNS
# ------------------------------------------------------------

print("\n[3/8] Validating inputs...")

if image_embeddings.ndim != 2 or image_embeddings.shape[1] != 1792:
    raise ValueError(
        f"Expected image embeddings (N, 1792); "
        f"got {image_embeddings.shape}"
    )

if satellite_sequences.ndim != 3 or satellite_sequences.shape[1:] != (10, 3):
    raise ValueError(
        f"Expected satellite sequences (N, 10, 3); "
        f"got {satellite_sequences.shape}"
    )

if background_raw_np.ndim != 3 or background_raw_np.shape[1:] != (10, 3):
    raise ValueError(
        f"Unexpected SHAP background shape: {background_raw_np.shape}"
    )

if not np.isfinite(image_embeddings).all():
    raise ValueError("Image embeddings contain NaN or infinite values.")

if not np.isfinite(satellite_sequences).all():
    raise ValueError("Satellite sequences contain invalid values.")

if not np.isfinite(background_raw_np).all():
    raise ValueError("SHAP background contains invalid values.")

required_dataset_columns = {
    "image_embedding_index",
    "nearest_satellite_field",
    "label_11class",
}

if not required_dataset_columns.issubset(dataset.columns):
    raise KeyError(
        "Missing dataset columns: "
        + str(sorted(required_dataset_columns - set(dataset.columns)))
    )

required_mapping_columns = {"field_id", "sequence_index"}

if not required_mapping_columns.issubset(field_mapping.columns):
    raise KeyError(
        "Missing mapping columns: "
        + str(sorted(required_mapping_columns - set(field_mapping.columns)))
    )

# Verify mapping uniqueness and valid indices.
if field_mapping["field_id"].duplicated().any():
    raise ValueError("Field mapping contains duplicate field_id values.")

if field_mapping["sequence_index"].duplicated().any():
    raise ValueError("Field mapping contains duplicate sequence_index values.")

mapping_indices = pd.to_numeric(
    field_mapping["sequence_index"],
    errors="raise"
)

if not np.all(mapping_indices.to_numpy() == np.floor(mapping_indices.to_numpy())):
    raise ValueError("Mapping sequence_index values must be integers.")

field_mapping = field_mapping.copy()
field_mapping["sequence_index"] = mapping_indices.astype(int)

if not field_mapping["sequence_index"].between(
    0, len(satellite_sequences) - 1
).all():
    raise ValueError("Field mapping has out-of-range sequence indices.")

# Build the field-to-sequence mapping.
field_to_sequence = dict(
    zip(field_mapping["field_id"], field_mapping["sequence_index"])
)

# Check that every dataset row can be linked to a satellite sequence.
unmapped_fields = (
    dataset["nearest_satellite_field"].isna()
    | ~dataset["nearest_satellite_field"].isin(field_to_sequence)
)

if unmapped_fields.any():
    raise ValueError(
        f"{int(unmapped_fields.sum())} dataset rows have no valid "
        "satellite field mapping."
    )

embedding_indices = pd.to_numeric(
    dataset["image_embedding_index"],
    errors="raise"
)

if not np.all(embedding_indices.to_numpy() == np.floor(embedding_indices.to_numpy())):
    raise ValueError("Image embedding indices must be integers.")

embedding_indices = embedding_indices.astype(int)

if not embedding_indices.between(
    0, len(image_embeddings) - 1
).all():
    raise ValueError("Dataset contains invalid image embedding indices.")

print("Input and mapping validation: PASSED")

# ------------------------------------------------------------
# 4. EXTRACT THE VERIFIED MODEL CLASS
# ------------------------------------------------------------

print("\n[4/8] Extracting model class...")

source_text = SOURCE_PATH.read_text(encoding="utf-8")
syntax_tree = ast.parse(source_text)

class_nodes = [
    node for node in syntax_tree.body
    if isinstance(node, ast.ClassDef)
    and node.name == "TemporalCrossAttentionModel"
]

if len(class_nodes) != 1:
    raise RuntimeError(
        "Expected one TemporalCrossAttentionModel class; "
        f"found {len(class_nodes)}."
    )

class_module = ast.Module(
    body=class_nodes,
    type_ignores=[]
)

ast.fix_missing_locations(class_module)

namespace = {
    "torch": torch,
    "nn": nn,
    "F": torch.nn.functional,
    "np": np,
}

exec(
    compile(class_module, str(SOURCE_PATH), "exec"),
    namespace
)

ModelClass = namespace["TemporalCrossAttentionModel"]

print("Model class:", ModelClass.__name__)
print("Constructor:", inspect.signature(ModelClass.__init__))

# ------------------------------------------------------------
# 5. LOAD CHECKPOINT STRICTLY
# ------------------------------------------------------------

print("\n[5/8] Loading model checkpoint...")

model = ModelClass(
    image_dim=int(checkpoint["image_dim"]),
    satellite_input_dim=int(checkpoint["satellite_input_dim"]),
    projection_dim=int(checkpoint["projection_dim"]),
    num_heads=int(checkpoint["num_heads"]),
    num_classes=int(checkpoint["num_classes"]),
)

model.load_state_dict(
    checkpoint["model_state_dict"],
    strict=True
)

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

model = model.to(device)
model.eval()

print("Strict checkpoint loading: PASSED")
print("Device:", device)

# ------------------------------------------------------------
# 6. NORMALIZE SATELLITE INPUTS
# ------------------------------------------------------------

print("\n[6/8] Preparing normalization...")

satellite_mean = torch.tensor(
    checkpoint["satellite_mean"],
    dtype=torch.float32,
    device=device
).view(1, 1, 3)

satellite_std = torch.tensor(
    checkpoint["satellite_std"],
    dtype=torch.float32,
    device=device
).view(1, 1, 3)

if not torch.isfinite(satellite_mean).all():
    raise ValueError("Satellite mean contains invalid values.")

if not torch.isfinite(satellite_std).all() or torch.any(satellite_std <= 0):
    raise ValueError("Satellite standard deviation is invalid.")

background_raw = torch.as_tensor(
    background_raw_np,
    dtype=torch.float32,
    device=device
)

background_normalized = (
    background_raw - satellite_mean
) / satellite_std

print("Raw background:", tuple(background_raw.shape))
print("Normalized background:", tuple(background_normalized.shape))

# ------------------------------------------------------------
# 7. SELECT A VALID IMAGE-SATELLITE PAIR
# ------------------------------------------------------------

print("\n[7/8] Selecting image-satellite pair...")

# Pick the first row with a valid label and valid mappings.
valid_rows = dataset.index[
    dataset["label_11class"].notna()
    & dataset["nearest_satellite_field"].notna()
]

if len(valid_rows) == 0:
    raise ValueError("No dataset row with a valid disease label was found.")

sample_index = int(valid_rows[0])
sample_row = dataset.iloc[sample_index]

embedding_index = int(sample_row["image_embedding_index"])
field_id = sample_row["nearest_satellite_field"]
sequence_index = int(field_to_sequence[field_id])
target_class = int(sample_row["label_11class"])

if not 0 <= target_class < int(checkpoint["num_classes"]):
    raise ValueError(f"Invalid target class: {target_class}")

fixed_image = torch.as_tensor(
    image_embeddings[embedding_index:embedding_index + 1],
    dtype=torch.float32,
    device=device
)

sample_satellite_raw = torch.as_tensor(
    satellite_sequences[sequence_index:sequence_index + 1],
    dtype=torch.float32,
    device=device
)

sample_satellite_normalized = (
    sample_satellite_raw - satellite_mean
) / satellite_std

class_names = checkpoint["class_names"]

print("Dataset row:", sample_index)
print("Image embedding index:", embedding_index)
print("Satellite field:", field_id)
print("Satellite sequence index:", sequence_index)
print("True label index:", target_class)
print("True label name:", class_names[target_class])

# ------------------------------------------------------------
# 8. CREATE SHAP WRAPPER AND TEST INFERENCE
# ------------------------------------------------------------

print("\n[8/8] Creating SHAP wrapper...")

class SatelliteClassWrapper(nn.Module):
    def __init__(self, base_model, image_embedding, target_class):
        super().__init__()

        self.base_model = base_model

        self.register_buffer(
            "fixed_image",
            image_embedding.detach().clone()
        )

        self.target_class = int(target_class)

    def forward(self, satellite_normalized):
        batch_size = satellite_normalized.shape[0]

        image_batch = self.fixed_image.expand(
            batch_size, -1
        )

        logits = self.base_model(
            image_batch,
            satellite_normalized
        )

        if isinstance(logits, (tuple, list)):
            logits = logits[0]

        return logits[:, self.target_class]

shap_model = SatelliteClassWrapper(
    model,
    fixed_image,
    target_class
).to(device)

shap_model.eval()

with torch.no_grad():
    sample_logits = model(
        fixed_image,
        sample_satellite_normalized
    )

    wrapper_output = shap_model(
        sample_satellite_normalized
    )

if isinstance(sample_logits, (tuple, list)):
    sample_logits = sample_logits[0]

if not torch.isfinite(sample_logits).all():
    raise RuntimeError("Model returned non-finite logits.")

if wrapper_output.shape != (1,):
    raise RuntimeError(
        f"Unexpected wrapper output shape: {wrapper_output.shape}"
    )

if not torch.isfinite(wrapper_output).all():
    raise RuntimeError("Wrapper output is not finite.")

if not torch.allclose(
    wrapper_output,
    sample_logits[:, target_class],
    atol=1e-5,
    rtol=1e-4
):
    raise RuntimeError("Wrapper output does not match model target logit.")

predicted_class = int(sample_logits.argmax(dim=1).item())

print("\nPrediction:", class_names[predicted_class])
print("Prediction index:", predicted_class)
print("Target class:", class_names[target_class])
print("Target logit:", float(wrapper_output.item()))
print("Wrapper output shape:", tuple(wrapper_output.shape))
print("Inference verification: PASSED")

# Save objects in the current Colab session for the next step.
# No model checkpoint or existing project file is modified.

print("\n" + "=" * 70)
print("STEP 10C-2 COMPLETED SUCCESSFULLY")
print("Model wrapper is ready for SHAP calculation.")
print("=" * 70)

