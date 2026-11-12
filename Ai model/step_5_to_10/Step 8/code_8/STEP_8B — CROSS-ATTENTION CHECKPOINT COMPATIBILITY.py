# ============================================================================
# STEP_8B — CROSS-ATTENTION CHECKPOINT COMPATIBILITY
# ============================================================================

import torch
from pathlib import Path

BASE = Path("/content/drive/MyDrive/final year project/Real_world_test/Step 7")

CHECKPOINTS = [
    BASE / "Step7J_Phase1_Training/step7J_phase1_cross_attention_best.pth",
    BASE / "Step7J_Phase1_Training/step7J_phase1_cross_attention_final.pth",
    BASE / "Step7K_Improved_Training/step7K_improved_cross_attention_final.pth",
    BASE / "Step7L_Temporal_CrossAttention/step7L_temporal_cross_attention_best.pth",
    BASE / "Step7L_Temporal_CrossAttention/step7L_temporal_cross_attention_final.pth",
    BASE / "Step7L_Temporal_CrossAttention_Improved/step7L_improved_best.pth",
    BASE / "Step7L_V3_Gated_CrossAttention/step7L_V3_best.pth",
    BASE / "Step7N_Temporal_CrossAttention/step7N_phase2_temporal_cross_attention_best.pth",
    BASE / "Step7N_Temporal_CrossAttention/step7N_phase2_temporal_cross_attention_final.pth",
]

print("=" * 100)
print("STEP 8B — CHECKPOINT COMPATIBILITY INSPECTION")
print("=" * 100)

for path in CHECKPOINTS:

    print("\n" + "-" * 100)
    print(path.name)
    print("-" * 100)

    if not path.exists():
        print("NOT FOUND")
        continue

    try:
        ckpt = torch.load(
            path,
            map_location="cpu",
            weights_only=False
        )

        print("Size:", round(path.stat().st_size / (1024 * 1024), 2), "MB")

        if isinstance(ckpt, dict):

            print("Checkpoint keys:")
            print(list(ckpt.keys()))

            if "model_state_dict" in ckpt:

                state = ckpt["model_state_dict"]

                print("\nState dict parameter count:", len(state))

                print("\nImportant parameter shapes:")

                for key, value in state.items():

                    if any(x in key.lower() for x in [
                        "image_projection",
                        "satellite_lstm",
                        "cross_attention",
                        "attention",
                        "classifier"
                    ]):

                        print(
                            key,
                            "->",
                            tuple(value.shape)
                            if hasattr(value, "shape")
                            else type(value)
                        )

            for key in [
                "epoch",
                "best_val_accuracy",
                "best_val_loss",
                "num_classes",
                "classes",
                "phase",
                "train_samples",
                "validation_samples"
            ]:

                if key in ckpt:
                    print(f"\n{key}:", ckpt[key])

        else:
            print("Checkpoint type:", type(ckpt))

    except Exception as e:
        print("LOAD ERROR:", repr(e))

print("\n" + "=" * 100)
print("CHECKPOINT INSPECTION COMPLETE")
print("=" * 100)