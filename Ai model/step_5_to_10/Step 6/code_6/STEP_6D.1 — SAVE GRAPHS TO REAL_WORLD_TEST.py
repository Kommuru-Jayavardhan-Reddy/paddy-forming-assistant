# ============================================================
# STEP_6D.1 — SAVE GRAPHS TO REAL_WORLD_TEST / STEP 6
# ============================================================

import os
import numpy as np
import matplotlib.pyplot as plt

# ------------------------------------------------------------
# 1. CREATE STEP 6 FOLDER
# ------------------------------------------------------------

STEP6_DIR = "/content/drive/MyDrive/final year project/Real_world_test/Step 6"

os.makedirs(STEP6_DIR, exist_ok=True)

print("Step 6 folder:")
print(STEP6_DIR)


# ------------------------------------------------------------
# 2. CONVERT EMBEDDINGS TO NUMPY
# ------------------------------------------------------------

projected_np = projected_embedding.detach().cpu().numpy()
normalized_np = satellite_embedding.detach().cpu().numpy()


# ============================================================
# GRAPH 1 — BEFORE LAYER NORMALIZATION
# ============================================================

plt.figure(figsize=(10, 6))

plt.hist(
    projected_np.flatten(),
    bins=50,
    alpha=0.8
)

plt.title("Satellite Embedding Distribution Before Layer Normalization")
plt.xlabel("Embedding Value")
plt.ylabel("Frequency")
plt.grid(True, alpha=0.3)

graph1_path = os.path.join(
    STEP6_DIR,
    "step6D_before_layernorm_distribution.png"
)

plt.savefig(
    graph1_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved:", graph1_path)


# ============================================================
# GRAPH 2 — AFTER LAYER NORMALIZATION
# ============================================================

plt.figure(figsize=(10, 6))

plt.hist(
    normalized_np.flatten(),
    bins=50,
    alpha=0.8
)

plt.title("Satellite Embedding Distribution After Layer Normalization")
plt.xlabel("Normalized Embedding Value")
plt.ylabel("Frequency")
plt.grid(True, alpha=0.3)

graph2_path = os.path.join(
    STEP6_DIR,
    "step6D_after_layernorm_distribution.png"
)

plt.savefig(
    graph2_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved:", graph2_path)


# ============================================================
# GRAPH 3 — BEFORE vs AFTER
# ============================================================

plt.figure(figsize=(10, 6))

plt.hist(
    projected_np.flatten(),
    bins=50,
    alpha=0.5,
    label="Before LayerNorm"
)

plt.hist(
    normalized_np.flatten(),
    bins=50,
    alpha=0.5,
    label="After LayerNorm"
)

plt.title("Satellite Embedding Distribution: Before vs After Layer Normalization")
plt.xlabel("Embedding Value")
plt.ylabel("Frequency")
plt.legend()
plt.grid(True, alpha=0.3)

graph3_path = os.path.join(
    STEP6_DIR,
    "step6D_before_vs_after_layernorm.png"
)

plt.savefig(
    graph3_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved:", graph3_path)


# ============================================================
# GRAPH 4 — MEAN AND STD COMPARISON
# ============================================================

before_mean = projected_np.mean()
before_std = projected_np.std()

after_mean = normalized_np.mean()
after_std = normalized_np.std()

plt.figure(figsize=(8, 6))

labels = [
    "Before Mean",
    "After Mean",
    "Before Std",
    "After Std"
]

values = [
    before_mean,
    after_mean,
    before_std,
    after_std
]

plt.bar(labels, values)

plt.title("Embedding Mean and Standard Deviation")
plt.ylabel("Value")
plt.grid(True, axis="y", alpha=0.3)

graph4_path = os.path.join(
    STEP6_DIR,
    "step6D_mean_std_comparison.png"
)

plt.savefig(
    graph4_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved:", graph4_path)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 60)
print("STEP 6D.1 GRAPHS SAVED SUCCESSFULLY")
print("=" * 60)

print("\nFolder:")
print(STEP6_DIR)

print("\nFiles:")

for file in sorted(os.listdir(STEP6_DIR)):
    print(" -", file)