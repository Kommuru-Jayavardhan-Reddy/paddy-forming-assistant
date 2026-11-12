# ============================================================
# STEP 6E.1 — FINAL SATELLITE BRANCH VERIFICATION + GRAPHS
# ============================================================

import os
import torch
import numpy as np
import matplotlib.pyplot as plt

print("=" * 70)
print("STEP 6E.1 — FINAL SATELLITE BRANCH VERIFICATION")
print("=" * 70)


# ============================================================
# 1. CREATE STEP 6 FOLDER
# ============================================================

STEP6_DIR = "/content/drive/MyDrive/final year project/Real_world_test/Step 6"

os.makedirs(STEP6_DIR, exist_ok=True)

print("\nStep 6 output folder:")
print(STEP6_DIR)


# ============================================================
# 2. VERIFY FINAL EMBEDDING
# ============================================================

print("\nFinal satellite embedding:")
print("Shape:", tuple(satellite_embedding.shape))

num_samples = satellite_embedding.shape[0]
embedding_dim = satellite_embedding.shape[1]

EXPECTED_EMBEDDING_DIM = 256

print("\nNumber of satellite sequences:", num_samples)
print("Embedding dimension:", embedding_dim)


# ============================================================
# 3. CHECK SHAPE
# ============================================================

shape_ok = (
    satellite_embedding.ndim == 2
    and embedding_dim == EXPECTED_EMBEDDING_DIM
)

print("\nExpected shape:")
print(f"({num_samples}, {EXPECTED_EMBEDDING_DIM})")

print("Shape correct:", shape_ok)


# ============================================================
# 4. CHECK NaN / INF
# ============================================================

nan_count = torch.isnan(satellite_embedding).sum().item()
inf_count = torch.isinf(satellite_embedding).sum().item()

print("\nNaN count:", nan_count)
print("Inf count:", inf_count)


# ============================================================
# 5. EMBEDDING STATISTICS
# ============================================================

embedding_mean = satellite_embedding.mean().item()
embedding_std = satellite_embedding.std().item()
embedding_min = satellite_embedding.min().item()
embedding_max = satellite_embedding.max().item()

print("\nEmbedding statistics:")
print("Mean :", embedding_mean)
print("Std  :", embedding_std)
print("Min  :", embedding_min)
print("Max  :", embedding_max)


# ============================================================
# 6. VERIFY EACH EMBEDDING
# ============================================================

all_embeddings_correct = True

print("\nEmbedding verification:")

for i in range(num_samples):

    current_shape = tuple(satellite_embedding[i].shape)

    correct = current_shape == (EXPECTED_EMBEDDING_DIM,)

    if not correct:
        all_embeddings_correct = False

    print(
        f"Sequence {i+1:02d}: {current_shape}",
        "✅" if correct else "❌"
    )


# ============================================================
# 7. SAMPLE COUNT CHECK
# ============================================================

sample_count_ok = num_samples == X_sat.shape[0]

print("\nSample count verification:")
print("Input sequences :", X_sat.shape[0])
print("Output embeddings:", num_samples)
print("Count matches   :", sample_count_ok)


# ============================================================
# 8. CONVERT TO NUMPY
# ============================================================

embedding_np = (
    satellite_embedding
    .detach()
    .cpu()
    .numpy()
)


# ============================================================
# GRAPH 1
# FINAL 256-D EMBEDDING DISTRIBUTION
# ============================================================

plt.figure(figsize=(10, 6))

plt.hist(
    embedding_np.flatten(),
    bins=60,
    alpha=0.8
)

plt.title(
    "Step 6E - Final Satellite Embedding Distribution"
)

plt.xlabel("Embedding Value")
plt.ylabel("Frequency")

plt.grid(True, alpha=0.3)

graph1_path = os.path.join(
    STEP6_DIR,
    "step6E_final_embedding_distribution.png"
)

plt.savefig(
    graph1_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("\nGraph 1 saved:")
print(graph1_path)


# ============================================================
# GRAPH 2
# MEAN EMBEDDING VALUE FOR EACH SATELLITE SEQUENCE
# ============================================================

sample_means = embedding_np.mean(axis=1)

plt.figure(figsize=(12, 6))

plt.plot(
    range(1, num_samples + 1),
    sample_means,
    marker="o",
    markersize=3
)

plt.title(
    "Step 6E - Mean Embedding Value per Satellite Sequence"
)

plt.xlabel("Satellite Sequence")
plt.ylabel("Mean Embedding Value")

plt.grid(True, alpha=0.3)

graph2_path = os.path.join(
    STEP6_DIR,
    "step6E_embedding_mean_per_sequence.png"
)

plt.savefig(
    graph2_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Graph 2 saved:")
print(graph2_path)


# ============================================================
# GRAPH 3
# STANDARD DEVIATION FOR EACH SATELLITE SEQUENCE
# ============================================================

sample_stds = embedding_np.std(axis=1)

plt.figure(figsize=(12, 6))

plt.plot(
    range(1, num_samples + 1),
    sample_stds,
    marker="o",
    markersize=3
)

plt.title(
    "Step 6E - Embedding Standard Deviation per Sequence"
)

plt.xlabel("Satellite Sequence")
plt.ylabel("Standard Deviation")

plt.grid(True, alpha=0.3)

graph3_path = os.path.join(
    STEP6_DIR,
    "step6E_embedding_std_per_sequence.png"
)

plt.savefig(
    graph3_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Graph 3 saved:")
print(graph3_path)


# ============================================================
# GRAPH 4
# 256-D EMBEDDING MAGNITUDE PER SEQUENCE
# ============================================================

embedding_norms = np.linalg.norm(
    embedding_np,
    axis=1
)

plt.figure(figsize=(12, 6))

plt.plot(
    range(1, num_samples + 1),
    embedding_norms,
    marker="o",
    markersize=3
)

plt.title(
    "Step 6E - 256-D Satellite Embedding Magnitude"
)

plt.xlabel("Satellite Sequence")
plt.ylabel("L2 Embedding Norm")

plt.grid(True, alpha=0.3)

graph4_path = os.path.join(
    STEP6_DIR,
    "step6E_embedding_magnitude.png"
)

plt.savefig(
    graph4_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Graph 4 saved:")
print(graph4_path)


# ============================================================
# 9. FINAL VERIFICATION
# ============================================================

print("\n" + "=" * 70)
print("STEP 6E — FINAL RESULT")
print("=" * 70)

if (
    shape_ok
    and nan_count == 0
    and inf_count == 0
    and all_embeddings_correct
    and sample_count_ok
):

    print(f"✅ Satellite sequences processed: {num_samples}")
    print("✅ Each sequence has one 256-dimensional embedding")
    print(
        f"✅ Final satellite embedding shape: "
        f"({num_samples}, 256)"
    )
    print("✅ No NaN values")
    print("✅ No Inf values")
    print("✅ Input/output sample count matches")
    print("✅ Satellite temporal information compressed")
    print("✅ Final satellite branch verified")
    print("✅ Step 6E graphs generated")
    print("✅ STEP 6E PASSED")
    print("✅ STEP 6 — SATELLITE BiLSTM BRANCH COMPLETED")

else:

    print("❌ STEP 6E FAILED")

    if not shape_ok:
        print("❌ Embedding shape incorrect")

    if nan_count != 0:
        print("❌ NaN values detected")

    if inf_count != 0:
        print("❌ Inf values detected")

    if not all_embeddings_correct:
        print("❌ Some embeddings are not 256-dimensional")

    if not sample_count_ok:
        print("❌ Input/output sample count mismatch")


# ============================================================
# 10. SHOW SAVED FILES
# ============================================================

print("\n" + "=" * 70)
print("STEP 6 GRAPH FILES")
print("=" * 70)

for filename in sorted(os.listdir(STEP6_DIR)):
    print("📊", filename)