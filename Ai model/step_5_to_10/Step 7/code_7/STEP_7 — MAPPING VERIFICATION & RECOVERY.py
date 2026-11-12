# ================================================================
# STEP 7 — MAPPING VERIFICATION & RECOVERY
# ================================================================
# Purpose:
#   Find the exact relationship:
#
#   IMAGE → GPS → FIELD → SATELLITE SEQUENCE → EMBEDDING INDEX
#
# IMPORTANT:
#   This step DOES NOT train any model.
#   This step DOES NOT create Step 7 pairs yet.
#   It only investigates and reconstructs the mapping.
# ================================================================

import os
import glob
import pandas as pd
import numpy as np

print("=" * 80)
print("STEP 7 — IMAGE ↔ GPS ↔ FIELD ↔ SATELLITE MAPPING VERIFICATION")
print("=" * 80)

# ------------------------------------------------
# 1. PROJECT DIRECTORIES
# ------------------------------------------------

BASE = "/content/drive/MyDrive/final year project/Real_world_test"

STEP5 = os.path.join(BASE, "Step 5")
STEP6 = os.path.join(BASE, "Step 6")

print("\n[1] DIRECTORIES")
print("-" * 80)

print("Step 5:", STEP5)
print("Step 6:", STEP6)

if not os.path.exists(STEP5):
    print("WARNING: Step 5 directory not found")

if not os.path.exists(STEP6):
    print("WARNING: Step 6 directory not found")


# ------------------------------------------------
# 2. FIND ALL RELEVANT FILES
# ------------------------------------------------

print("\n" + "=" * 80)
print("[2] SEARCHING FOR MAPPING-RELATED FILES")
print("=" * 80)

extensions = [
    "*.csv",
    "*.npy",
    "*.npz",
    "*.txt",
    "*.json",
    "*.pkl"
]

files = []

for folder in [STEP5, STEP6]:

    if not os.path.exists(folder):
        continue

    for ext in extensions:
        files.extend(
            glob.glob(
                os.path.join(folder, "**", ext),
                recursive=True
            )
        )

files = sorted(set(files))

print(f"\nTotal relevant files found: {len(files)}")

for i, f in enumerate(files, 1):
    print(f"{i:3d}. {f}")


# ------------------------------------------------
# 3. IDENTIFY FILES USING KEYWORDS
# ------------------------------------------------

print("\n" + "=" * 80)
print("[3] IMPORTANT MAPPING FILES")
print("=" * 80)

keywords = [
    "gps",
    "field",
    "mapping",
    "satellite",
    "sequence",
    "embedding",
    "pair",
    "location",
    "gee"
]

mapping_files = []

for f in files:

    name = os.path.basename(f).lower()

    if any(k in name for k in keywords):
        mapping_files.append(f)

for i, f in enumerate(mapping_files, 1):
    print(f"{i:3d}. {f}")

print(f"\nMapping-related files: {len(mapping_files)}")


# ------------------------------------------------
# 4. INSPECT CSV FILES
# ------------------------------------------------

print("\n" + "=" * 80)
print("[4] CSV STRUCTURE INSPECTION")
print("=" * 80)

csv_files = [
    f for f in mapping_files
    if f.lower().endswith(".csv")
]

csv_data = {}

for f in csv_files:

    print("\n" + "-" * 80)
    print("FILE:", f)

    try:

        df = pd.read_csv(f)

        csv_data[f] = df

        print("Rows:", len(df))
        print("Columns:")

        for col in df.columns:
            print("   -", col)

        print("\nFirst 3 rows:")
        print(df.head(3).to_string(index=False))

    except Exception as e:

        print("Could not read CSV:", e)


# ------------------------------------------------
# 5. FIND COLUMNS THAT CAN DEFINE MAPPING
# ------------------------------------------------

print("\n" + "=" * 80)
print("[5] MAPPING COLUMN DETECTION")
print("=" * 80)

possible_mapping_terms = [
    "image",
    "filename",
    "file",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "field",
    "sequence",
    "satellite",
    "embedding",
    "index",
    "gps",
    "location"
]

for f, df in csv_data.items():

    found = []

    for col in df.columns:

        col_lower = str(col).lower()

        if any(term in col_lower for term in possible_mapping_terms):
            found.append(col)

    if found:

        print("\nFILE:")
        print(f)

        print("Potential mapping columns:")
        for col in found:
            print("   ", col)


# ------------------------------------------------
# 6. SEARCH SPECIFIC SATELLITE EMBEDDINGS
# ------------------------------------------------

print("\n" + "=" * 80)
print("[6] SATELLITE EMBEDDING FILES")
print("=" * 80)

embedding_files = []

for f in files:

    name = os.path.basename(f).lower()

    if (
        "satellite" in name
        and "embedding" in name
        and f.endswith(".npy")
    ):
        embedding_files.append(f)

for f in embedding_files:

    print("\nFILE:", f)

    try:

        arr = np.load(f)

        print("Shape:", arr.shape)
        print("dtype:", arr.dtype)
        print("NaN:", np.isnan(arr).sum())
        print("Inf:", np.isinf(arr).sum())

        if arr.ndim >= 2:
            print("Number of embeddings:", arr.shape[0])
            print("Embedding dimension:", arr.shape[1])

    except Exception as e:

        print("Could not load:", e)


# ------------------------------------------------
# 7. SPECIFICALLY FIND 58 × 256 EMBEDDING
# ------------------------------------------------

print("\n" + "=" * 80)
print("[7] SEARCHING FOR 58 × 256 SATELLITE EMBEDDING")
print("=" * 80)

target_embedding_files = []

for f in files:

    if not f.endswith(".npy"):
        continue

    try:

        arr = np.load(f)

        if arr.shape == (58, 256):

            target_embedding_files.append(f)

            print("\nFOUND EXACT 58 × 256 FILE:")
            print(f)
            print("Shape:", arr.shape)

    except:
        pass

if len(target_embedding_files) == 0:

    print("\nNo exact (58, 256) embedding file found.")

else:

    print(
        f"\nTotal exact 58 × 256 files: "
        f"{len(target_embedding_files)}"
    )


# ------------------------------------------------
# 8. FIND FILES WITH 58 RECORDS
# ------------------------------------------------

print("\n" + "=" * 80)
print("[8] SEARCHING FOR 58-RECORD MAPPING FILES")
print("=" * 80)

files_with_58 = []

for f, df in csv_data.items():

    if len(df) == 58:

        files_with_58.append(f)

        print("\nFOUND 58-ROW FILE:")
        print(f)

        print("Columns:", list(df.columns))

        print("\nPreview:")
        print(df.head(10).to_string(index=False))


# ------------------------------------------------
# 9. FIND FILES WITH 127 RECORDS
# ------------------------------------------------

print("\n" + "=" * 80)
print("[9] SEARCHING FOR 127-RECORD FILES")
print("=" * 80)

files_with_127 = []

for f, df in csv_data.items():

    if len(df) == 127:

        files_with_127.append(f)

        print("\nFOUND 127-ROW FILE:")
        print(f)

        print("Columns:", list(df.columns))

        print("\nPreview:")
        print(df.head(5).to_string(index=False))


# ------------------------------------------------
# 10. FIND FIELD INFORMATION
# ------------------------------------------------

print("\n" + "=" * 80)
print("[10] FIELD DISTRIBUTION")
print("=" * 80)

for f, df in csv_data.items():

    field_columns = [
        c for c in df.columns
        if "field" in str(c).lower()
    ]

    if not field_columns:
        continue

    for col in field_columns:

        print("\nFILE:", f)
        print("FIELD COLUMN:", col)

        print(
            df[col]
            .value_counts(dropna=False)
            .head(30)
            .to_string()
        )


# ------------------------------------------------
# 11. FIND SATELLITE SEQUENCE INFORMATION
# ------------------------------------------------

print("\n" + "=" * 80)
print("[11] SATELLITE SEQUENCE INFORMATION")
print("=" * 80)

for f, df in csv_data.items():

    sequence_columns = [
        c for c in df.columns
        if (
            "sequence" in str(c).lower()
            or "satellite" in str(c).lower()
        )
    ]

    if not sequence_columns:
        continue

    print("\nFILE:", f)

    for col in sequence_columns:

        print("\nCOLUMN:", col)

        print(
            df[col]
            .value_counts(dropna=False)
            .head(30)
            .to_string()
        )


# ------------------------------------------------
# 12. FINAL SUMMARY
# ------------------------------------------------

print("\n" + "=" * 80)
print("MAPPING INVESTIGATION SUMMARY")
print("=" * 80)

print("\nTotal files scanned:", len(files))
print("CSV files:", len(csv_files))
print("Mapping-related files:", len(mapping_files))
print("58-row CSV files:", len(files_with_58))
print("127-row CSV files:", len(files_with_127))
print("58 × 256 embedding files:", len(target_embedding_files))

print("\n" + "=" * 80)
print("IMPORTANT")
print("=" * 80)

print("""
DO NOT CREATE STEP 7 PAIRS YET.

First verify:

1. Which 58 images are the final images?
2. Which GPS coordinate belongs to each image?
3. Which FINAL_FIELD belongs to each image?
4. Which satellite sequence belongs to each field?
5. Which embedding index belongs to each satellite sequence?

Only after these five relationships are confirmed,
we will generate the final Step 7 mapping CSV.
""")

print("=" * 80)
print("MAPPING VERIFICATION COMPLETED")
print("=" * 80)