# =============================================================================
# STEP_7B — VERIFY EFFICIENTNET-B4 PHASE-C CHECKPOINT
# =============================================================================

import os
import torch

CHECKPOINT = "/content/drive/MyDrive/final year project/models/dl/efficientnet_b4_phaseC_best.pth"

print("=" * 80)
print("STEP 7B — EFFICIENTNET-B4 PHASE-C CHECKPOINT VERIFICATION")
print("=" * 80)

# -------------------------------------------------------------------------
# 1. Check file
# -------------------------------------------------------------------------

print("\n[1] CHECKPOINT FILE")
print("-" * 80)

if not os.path.exists(CHECKPOINT):
    raise FileNotFoundError(f"Checkpoint not found:\n{CHECKPOINT}")

size_mb = os.path.getsize(CHECKPOINT) / (1024 * 1024)

print(f"File : {CHECKPOINT}")
print(f"Size : {size_mb:.2f} MB")
print("✓ Checkpoint exists")


# -------------------------------------------------------------------------
# 2. Load checkpoint
# -------------------------------------------------------------------------

print("\n[2] LOADING CHECKPOINT")
print("-" * 80)

checkpoint = torch.load(
    CHECKPOINT,
    map_location="cpu"
)

print("✓ Checkpoint loaded")
print(f"Checkpoint Python type: {type(checkpoint)}")


# -------------------------------------------------------------------------
# 3. Inspect checkpoint structure
# -------------------------------------------------------------------------

print("\n[3] CHECKPOINT STRUCTURE")
print("-" * 80)

if isinstance(checkpoint, dict):

    print("Dictionary keys:")

    for key in checkpoint.keys():
        print(f"  - {key}")

else:

    print("Checkpoint is not a dictionary.")


# -------------------------------------------------------------------------
# 4. Inspect common state-dict locations
# -------------------------------------------------------------------------

print("\n[4] STATE-DICT INSPECTION")
print("-" * 80)

state_dict = None

if isinstance(checkpoint, dict):

    possible_keys = [
        "state_dict",
        "model_state_dict",
        "model",
        "net",
        "weights"
    ]

    for key in possible_keys:

        if key in checkpoint:

            candidate = checkpoint[key]

            if isinstance(candidate, dict):

                state_dict = candidate

                print(f"✓ Found state dictionary under key: '{key}'")
                break


if state_dict is None:

    if isinstance(checkpoint, dict):

        # Check whether checkpoint itself looks like a state_dict
        tensor_values = [
            value for value in checkpoint.values()
            if torch.is_tensor(value)
        ]

        if len(tensor_values) > 0:

            state_dict = checkpoint

            print("✓ Checkpoint itself appears to be a state_dict")


if state_dict is None:

    print("⚠️ State dictionary could not be identified.")

else:

    print(f"Number of parameters/tensors: {len(state_dict)}")

    print("\nFirst 15 parameter names:")

    for i, key in enumerate(state_dict.keys()):

        if i >= 15:
            break

        value = state_dict[key]

        if torch.is_tensor(value):
            print(f"  {key} : {tuple(value.shape)}")
        else:
            print(f"  {key} : {type(value)}")


# -------------------------------------------------------------------------
# 5. Search checkpoint metadata
# -------------------------------------------------------------------------

print("\n[5] TRAINING METADATA")
print("-" * 80)

if isinstance(checkpoint, dict):

    metadata_keys = [
        "epoch",
        "best_val_accuracy",
        "val_accuracy",
        "accuracy",
        "num_classes",
        "class_names",
        "classes",
        "embedding_dim",
        "feature_dim"
    ]

    found_metadata = False

    for key in metadata_keys:

        if key in checkpoint:

            print(f"{key}: {checkpoint[key]}")
            found_metadata = True

    if not found_metadata:
        print("No common training metadata found.")

else:

    print("No metadata available.")


# -------------------------------------------------------------------------
# 6. Final status
# -------------------------------------------------------------------------

print("\n" + "=" * 80)
print("STEP 7B RESULT")
print("=" * 80)

if state_dict is not None:

    print("""
✓ EfficientNet-B4 Phase-C checkpoint successfully loaded.
✓ State dictionary identified.

Next:
    Build the SAME EfficientNet-B4 architecture
    → load this checkpoint
    → remove/use the classifier only for feature extraction
    → verify output dimension = 1792
    → generate embeddings for the 641 confirmed images.

NO RETRAINING will be performed.
""")

else:

    print("""
⚠️ Checkpoint loaded, but state-dict structure needs inspection.

DO NOT generate embeddings yet.
""")

print("=" * 80)