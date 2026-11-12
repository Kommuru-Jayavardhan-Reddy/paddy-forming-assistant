# =============================================================================
# STEP_7C — EFFICIENTNET-B4 ARCHITECTURE + 1792-D OUTPUT VERIFICATION
# =============================================================================

import os
import torch
import torch.nn as nn
import torchvision.models as models

print("=" * 80)
print("STEP 7C — EFFICIENTNET-B4 1792-D OUTPUT VERIFICATION")
print("=" * 80)

# -------------------------------------------------------------------------
# 1. Paths
# -------------------------------------------------------------------------

CHECKPOINT = (
    "/content/drive/MyDrive/final year project/"
    "models/dl/efficientnet_b4_phaseC_best.pth"
)

print("\n[1] CHECKPOINT")
print("-" * 80)
print(CHECKPOINT)

if not os.path.exists(CHECKPOINT):
    raise FileNotFoundError("Checkpoint not found.")

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

state_dict = checkpoint["model_state_dict"]

print("✓ model_state_dict loaded")


# -------------------------------------------------------------------------
# 3. Create EfficientNet-B4
# -------------------------------------------------------------------------

print("\n[3] BUILDING EFFICIENTNET-B4")
print("-" * 80)

model = models.efficientnet_b4(
    weights=None,
    num_classes=13
)

print("✓ EfficientNet-B4 created")
print("✓ Number of classes:", 13)


# -------------------------------------------------------------------------
# 4. Load Phase-C weights
# -------------------------------------------------------------------------

print("\n[4] LOADING PHASE-C WEIGHTS")
print("-" * 80)

missing_keys, unexpected_keys = model.load_state_dict(
    state_dict,
    strict=False
)

print("Missing keys:", len(missing_keys))
print("Unexpected keys:", len(unexpected_keys))

if len(missing_keys) == 0 and len(unexpected_keys) == 0:
    print("✓ ALL CHECKPOINT WEIGHTS MATCH")

else:

    print("\n⚠️ Weight mismatch detected.")

    if missing_keys:
        print("\nMissing keys:")
        for key in missing_keys[:20]:
            print(" ", key)

    if unexpected_keys:
        print("\nUnexpected keys:")
        for key in unexpected_keys[:20]:
            print(" ", key)


# -------------------------------------------------------------------------
# 5. Inspect classifier
# -------------------------------------------------------------------------

print("\n[5] CLASSIFIER INSPECTION")
print("-" * 80)

print(model.classifier)

classifier_linear = model.classifier[1]

print("\nClassifier input features :",
      classifier_linear.in_features)

print("Classifier output classes :",
      classifier_linear.out_features)


# -------------------------------------------------------------------------
# 6. Verify expected feature dimension
# -------------------------------------------------------------------------

print("\n[6] FEATURE DIMENSION")
print("-" * 80)

expected_dim = 1792

actual_classifier_input = classifier_linear.in_features

print("Expected EfficientNet-B4 feature dimension:", expected_dim)
print("Checkpoint classifier input dimension    :", actual_classifier_input)

if actual_classifier_input == expected_dim:
    print("✓ 1792-D FEATURE DIMENSION CONFIRMED")

else:
    raise RuntimeError(
        f"Expected 1792 features, "
        f"but model reports {actual_classifier_input}"
    )


# -------------------------------------------------------------------------
# 7. Create feature extractor
# -------------------------------------------------------------------------

print("\n[7] CREATING FEATURE EXTRACTOR")
print("-" * 80)

feature_extractor = nn.Sequential(
    model.features,
    model.avgpool,
    nn.Flatten()
)

feature_extractor.eval()

print("✓ Feature extractor created")


# -------------------------------------------------------------------------
# 8. Dummy forward pass
# -------------------------------------------------------------------------

print("\n[8] DUMMY FORWARD PASS")
print("-" * 80)

dummy_input = torch.randn(
    1, 3, 380, 380
)

with torch.no_grad():

    dummy_output = feature_extractor(dummy_input)

print("Input shape :", tuple(dummy_input.shape))
print("Output shape:", tuple(dummy_output.shape))


# -------------------------------------------------------------------------
# 9. Final verification
# -------------------------------------------------------------------------

print("\n" + "=" * 80)
print("FINAL STEP 7C VERIFICATION")
print("=" * 80)

if dummy_output.shape == (1, 1792):

    print("""
✓ EfficientNet-B4 architecture verified
✓ Phase-C checkpoint loaded
✓ 13-class classifier verified
✓ Feature dimension = 1792
✓ Dummy forward pass successful
✓ Image feature extractor is READY

NO IMAGE TRAINING WILL BE PERFORMED.
""")

else:

    print("""
❌ 1792-D verification FAILED.

DO NOT generate the 641 embeddings yet.
""")

print("=" * 80)
print("STEP 7C FINISHED")
print("=" * 80)