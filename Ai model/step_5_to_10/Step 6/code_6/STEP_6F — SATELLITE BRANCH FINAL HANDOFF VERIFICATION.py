# ============================================================
# STEP 6F — SATELLITE BRANCH FINAL HANDOFF VERIFICATION
# ============================================================

import os
import torch
import numpy as np
import matplotlib.pyplot as plt

print("=" * 75)
print("STEP 6F — SATELLITE BRANCH FINAL HANDOFF VERIFICATION")
print("=" * 75)


# ============================================================
# 1. STEP 6 OUTPUT FOLDER
# ============================================================

STEP6_DIR = (
    "/content/drive/MyDrive/"
    "final year project/Real_world_test/Step 6"
)

os.makedirs(STEP6_DIR, exist_ok=True)

print("\nOutput folder:")
print(STEP6_DIR)


# ============================================================
# 2. CHECK INPUT SATELLITE DATA
# ============================================================

print("\n" + "-" * 75)
print("1. SATELLITE INPUT CHECK")
print("-" * 75)

print("X_sat shape:", tuple(X_sat.shape))

input_shape_ok = (
    X_sat.ndim == 3
    and X_sat.shape[1] == 10
    and X_sat.shape[2] == 3
)

print("Expected format: (N, 10, 3)")
print("Input shape correct:", input_shape_ok)


# ============================================================
# 3. CHECK FINAL SATELLITE EMBEDDING
# ============================================================

print("\n" + "-" * 75)
print("2. FINAL EMBEDDING CHECK")
print("-" * 75)

print(
    "Satellite embedding shape:",
    tuple(satellite_embedding.shape)
)

num_sequences = satellite_embedding.shape[0]
embedding_dimension = satellite_embedding.shape[1]

embedding_shape_ok = (
    satellite_embedding.ndim == 2
    and embedding_dimension == 256
)

print(
    "Expected format:",
    f"({num_sequences}, 256)"
)

print(
    "Embedding shape correct:",
    embedding_shape_ok
)


# ============================================================
# 4. INPUT → OUTPUT SAMPLE COUNT
# ============================================================

print("\n" + "-" * 75)
print("3. INPUT / OUTPUT COUNT CHECK")
print("-" * 75)

input_count = X_sat.shape[0]
output_count = satellite_embedding.shape[0]

count_match = input_count == output_count

print("Input sequences :", input_count)
print("Output embeddings:", output_count)
print("Count matches    :", count_match)


# ============================================================
# 5. NUMERICAL STABILITY
# ============================================================

print("\n" + "-" * 75)
print("4. NUMERICAL STABILITY CHECK")
print("-" * 75)

nan_count = torch.isnan(satellite_embedding).sum().item()
inf_count = torch.isinf(satellite_embedding).sum().item()

print("NaN count:", nan_count)
print("Inf count:", inf_count)

numerical_ok = (
    nan_count == 0
    and inf_count == 0
)

print("Numerically stable:", numerical_ok)


# ============================================================
# 6. EMBEDDING STATISTICS
# ============================================================

embedding_np = (
    satellite_embedding
    .detach()
    .cpu()
    .numpy()
)

global_mean = float(embedding_np.mean())
global_std = float(embedding_np.std())
global_min = float(embedding_np.min())
global_max = float(embedding_np.max())

print("\n" + "-" * 75)
print("5. FINAL EMBEDDING STATISTICS")
print("-" * 75)

print(f"Mean : {global_mean:.6f}")
print(f"Std  : {global_std:.6f}")
print(f"Min  : {global_min:.6f}")
print(f"Max  : {global_max:.6f}")


# ============================================================
# 7. PER-SEQUENCE EMBEDDING CHECK
# ============================================================

print("\n" + "-" * 75)
print("6. PER-SEQUENCE 256-D CHECK")
print("-" * 75)

all_256 = True

for i in range(num_sequences):

    current_dimension = embedding_np[i].shape[0]

    if current_dimension != 256:
        all_256 = False

print(
    "Every satellite sequence has 256 dimensions:",
    all_256
)


# ============================================================
# 8. FINAL EMBEDDING NORMS
# ============================================================

embedding_norms = np.linalg.norm(
    embedding_np,
    axis=1
)

print("\nEmbedding norm statistics:")

print(
    "Minimum norm:",
    f"{embedding_norms.min():.6f}"
)

print(
    "Maximum norm:",
    f"{embedding_norms.max():.6f}"
)

print(
    "Mean norm:",
    f"{embedding_norms.mean():.6f}"
)


# ============================================================
# GRAPH — FINAL EMBEDDING NORM
# ============================================================

plt.figure(figsize=(12, 6))

plt.plot(
    range(1, num_sequences + 1),
    embedding_norms,
    marker="o",
    markersize=3
)

plt.title(
    "Step 6F - Final Satellite Embedding Norm"
)

plt.xlabel("Satellite Sequence")
plt.ylabel("L2 Embedding Norm")

plt.grid(True, alpha=0.3)

graph_path = os.path.join(
    STEP6_DIR,
    "step6F_final_embedding_norm.png"
)

plt.savefig(
    graph_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("\nGraph saved:")
print(graph_path)


# ============================================================
# 9. SAVE FINAL EMBEDDINGS
# ============================================================

embedding_path = os.path.join(
    STEP6_DIR,
    "step6F_final_satellite_embeddings.npy"
)

np.save(
    embedding_path,
    embedding_np
)

print("\nFinal embeddings saved:")
print(embedding_path)


# ============================================================
# 10. SAVE VERIFICATION SUMMARY
# ============================================================

summary_path = os.path.join(
    STEP6_DIR,
    "step6F_verification_summary.txt"
)

with open(summary_path, "w") as f:

    f.write(
        "STEP 6F — SATELLITE BRANCH FINAL HANDOFF VERIFICATION\n"
    )

    f.write("=" * 70 + "\n\n")

    f.write(
        f"Input satellite shape : {tuple(X_sat.shape)}\n"
    )

    f.write(
        f"Final embedding shape : "
        f"{tuple(satellite_embedding.shape)}\n"
    )

    f.write(
        f"Number of sequences  : {num_sequences}\n"
    )

    f.write(
        f"Embedding dimension  : {embedding_dimension}\n"
    )

    f.write(
        f"NaN count            : {nan_count}\n"
    )

    f.write(
        f"Inf count            : {inf_count}\n"
    )

    f.write(
        f"Mean                 : {global_mean:.6f}\n"
    )

    f.write(
        f"Std                  : {global_std:.6f}\n"
    )

    f.write(
        f"Min                  : {global_min:.6f}\n"
    )

    f.write(
        f"Max                  : {global_max:.6f}\n"
    )

    f.write(
        f"Input/output match   : {count_match}\n"
    )

    f.write(
        f"All embeddings 256-D : {all_256}\n"
    )

    f.write(
        f"Numerically stable   : {numerical_ok}\n"
    )

    f.write("\n")


# ============================================================
# 11. FINAL STEP 6F VERIFICATION
# ============================================================

final_pass = (
    input_shape_ok
    and embedding_shape_ok
    and count_match
    and numerical_ok
    and all_256
)


print("\n" + "=" * 75)
print("STEP 6F — FINAL RESULT")
print("=" * 75)

if final_pass:

    print("✅ Satellite input verified")
    print("✅ Temporal sequence length = 10")
    print("✅ Satellite features = 3")
    print("✅ Input/output sequence count matches")
    print("✅ Final embedding dimension = 256")
    print("✅ All embeddings are 256-D")
    print("✅ No NaN values")
    print("✅ No Inf values")
    print("✅ Final embedding graph saved")
    print("✅ Final embeddings saved")
    print("✅ Verification summary saved")
    print("✅ STEP 6F PASSED")
    print("✅ STEP 6 — SATELLITE BiLSTM BRANCH COMPLETED")

else:

    print("❌ STEP 6F FAILED")

    if not input_shape_ok:
        print("❌ Satellite input shape problem")

    if not embedding_shape_ok:
        print("❌ Final embedding shape problem")

    if not count_match:
        print("❌ Input/output sequence count mismatch")

    if not numerical_ok:
        print("❌ NaN or Inf detected")

    if not all_256:
        print("❌ Some embeddings are not 256-dimensional")


# ============================================================
# 12. SHOW STEP 6 FILES
# ============================================================

print("\n" + "=" * 75)
print("STEP 6 OUTPUT FILES")
print("=" * 75)

for filename in sorted(os.listdir(STEP6_DIR)):
    print("📁", filename)