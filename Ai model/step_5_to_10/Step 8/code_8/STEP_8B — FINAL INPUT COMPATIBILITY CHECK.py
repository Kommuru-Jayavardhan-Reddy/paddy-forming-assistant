# ============================================================================
# STEP 8B — FINAL INPUT COMPATIBILITY CHECK
# ============================================================================

import numpy as np
import pandas as pd
import os

SAT_PATH = "/content/drive/MyDrive/final year project/Real_world_test/Step 5/bilstm_sequences.npy"

IMAGE_EMB_PATH = "/content/drive/MyDrive/final year project/Real_world_test/Step 7/step7_FINAL_image_embeddings_1792.npy"

MAPPING_PATH = "/content/drive/MyDrive/final year project/Real_world_test/Step 7/step7_FINAL_image_field_satellite_mapping.csv"

print("=" * 100)
print("STEP 8B — FINAL INPUT COMPATIBILITY CHECK")
print("=" * 100)

# --------------------------------------------------------------------------
# 1. SATELLITE SEQUENCES
# --------------------------------------------------------------------------

print("\n[1] SATELLITE SEQUENCES")
print("-" * 90)

sat = np.load(SAT_PATH)

print("Path:", SAT_PATH)
print("Shape:", sat.shape)
print("Dtype:", sat.dtype)
print("NaN:", np.isnan(sat).any())
print("Inf:", np.isinf(sat).any())

# --------------------------------------------------------------------------
# 2. IMAGE EMBEDDINGS
# --------------------------------------------------------------------------

print("\n[2] IMAGE EMBEDDINGS")
print("-" * 90)

img = np.load(IMAGE_EMB_PATH)

print("Path:", IMAGE_EMB_PATH)
print("Shape:", img.shape)
print("Dtype:", img.dtype)
print("NaN:", np.isnan(img).any())
print("Inf:", np.isinf(img).any())

# --------------------------------------------------------------------------
# 3. MAPPING CSV
# --------------------------------------------------------------------------

print("\n[3] IMAGE / FIELD / SATELLITE MAPPING")
print("-" * 90)

df = pd.read_csv(MAPPING_PATH)

print("Path:", MAPPING_PATH)
print("Shape:", df.shape)

print("\nColumns:")
for c in df.columns:
    print(" -", c)

# --------------------------------------------------------------------------
# 4. FIRST 5 ROWS
# --------------------------------------------------------------------------

print("\n[4] FIRST 5 MAPPING ROWS")
print("-" * 90)

print(df.head().to_string())

# --------------------------------------------------------------------------
# 5. FIELD INFORMATION
# --------------------------------------------------------------------------

print("\n[5] FIELD INFORMATION")
print("-" * 90)

for col in df.columns:
    if "field" in col.lower():
        print("\nField column:", col)
        print(df[col].value_counts(dropna=False).to_string())

# --------------------------------------------------------------------------
# 6. SATELLITE INDEX INFORMATION
# --------------------------------------------------------------------------

print("\n[6] SATELLITE INDEX / SEQUENCE INFORMATION")
print("-" * 90)

for col in df.columns:

    if any(x in col.lower() for x in [
        "satellite",
        "sequence",
        "embedding",
        "field"
    ]):

        print("\nColumn:", col)
        print(df[col].head(10).to_string())

# --------------------------------------------------------------------------
# 7. IMAGE COUNT VS EMBEDDING COUNT
# --------------------------------------------------------------------------

print("\n[7] COUNT COMPATIBILITY")
print("-" * 90)

print("Mapping rows:", len(df))
print("Image embeddings:", len(img))
print("Satellite sequences:", len(sat))

if len(df) == len(img):
    print("IMAGE COUNT MATCH: YES")
else:
    print("IMAGE COUNT MATCH: NO")

# --------------------------------------------------------------------------
# FINAL
# --------------------------------------------------------------------------

print("\n" + "=" * 100)
print("INPUT COMPATIBILITY CHECK COMPLETE")
print("=" * 100)