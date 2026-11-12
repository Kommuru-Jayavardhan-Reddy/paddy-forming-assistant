# ============================================================================
# STEP 7.3- FINAL IMAGE → FIELD → SATELLITE EMBEDDING MAPPING
# ============================================================================
# FINAL CLEAN MAPPING
#
# Flow:
#
# Original GPS image
#       ↓
# Confirmed GPS field
#       ↓
# Trusted satellite field
#       ↓
# Existing Step 6 satellite embedding (256-D)
#
# IMPORTANT:
# - Step 6 is NOT rerun
# - Original GPS is NOT modified
# - Rejected GPS fields are NOT used
# - Only CONFIRMED image mappings are used
# ============================================================================

import os
import numpy as np
import pandas as pd

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = "/content/drive/MyDrive/final year project/Real_world_test"

STEP5_DIR = os.path.join(
    BASE_DIR,
    "Step 5"
)

STEP6_DIR = os.path.join(
    BASE_DIR,
    "Step 6"
)

STEP7_DIR = os.path.join(
    BASE_DIR,
    "Step 7"
)

os.makedirs(
    STEP7_DIR,
    exist_ok=True
)

# --------------------------------------------------------------------------
# STEP 5C.3 IMAGE MAPPING
# --------------------------------------------------------------------------

IMAGE_MAPPING_FILE = os.path.join(
    STEP5_DIR,
    "step5C3_image_to_satellite_mapping_candidates.csv"
)

# --------------------------------------------------------------------------
# STEP 5C.3 FIELD MAPPING
# --------------------------------------------------------------------------

FIELD_MAPPING_FILE = os.path.join(
    STEP5_DIR,
    "step5C3_gps_field_to_satellite_mapping.csv"
)

# --------------------------------------------------------------------------
# TRUSTED SATELLITE FIELD FILE
# --------------------------------------------------------------------------

SATELLITE_FIELD_FILE = os.path.join(
    STEP5_DIR,
    "clean_field_candidates_renamed.csv"
)

# --------------------------------------------------------------------------
# SENTINEL TIME SERIES
# --------------------------------------------------------------------------

TIMESERIES_FILE = os.path.join(
    STEP5_DIR,
    "sentinel2_timeseries.csv"
)

# --------------------------------------------------------------------------
# STEP 6 FINAL EMBEDDINGS
# --------------------------------------------------------------------------

EMBEDDING_FILE = os.path.join(
    STEP6_DIR,
    "step6F_final_satellite_embeddings.npy"
)

# ============================================================================
# OUTPUTS
# ============================================================================

FINAL_MAPPING_FILE = os.path.join(
    STEP7_DIR,
    "step7_FINAL_image_field_satellite_mapping.csv"
)

FINAL_EMBEDDING_FILE = os.path.join(
    STEP7_DIR,
    "step7_FINAL_satellite_embeddings.npy"
)

IMAGE_EMBEDDING_INDEX_FILE = os.path.join(
    STEP7_DIR,
    "step7_FINAL_image_embedding_index.csv"
)

VERIFICATION_FILE = os.path.join(
    STEP7_DIR,
    "step7_FINAL_mapping_verification.txt"
)

SUMMARY_FILE = os.path.join(
    STEP7_DIR,
    "step7_FINAL_mapping_summary.csv"
)

# ============================================================================
# HEADER
# ============================================================================

print("=" * 80)
print("STEP 7 — FINAL IMAGE → FIELD → SATELLITE EMBEDDING MAPPING")
print("=" * 80)

# ============================================================================
# LOAD STEP 5C.3 IMAGE MAPPING
# ============================================================================

print("\n[1] Loading Step 5C.3 image mapping...")

image_df = pd.read_csv(
    IMAGE_MAPPING_FILE
)

print(
    f"Total candidate image records: {len(image_df)}"
)

# ============================================================================
# CHECK REQUIRED COLUMNS
# ============================================================================

required_image_columns = [
    "gps_field_id",
    "nearest_satellite_field",
    "distance_km",
    "decision"
]

for col in required_image_columns:

    if col not in image_df.columns:

        raise ValueError(
            f"Missing required column: {col}\n"
            f"Available columns:\n{list(image_df.columns)}"
        )

# ============================================================================
# KEEP ONLY CONFIRMED
# ============================================================================

confirmed_df = image_df[
    image_df["decision"] == "CONFIRMED"
].copy()

print(
    f"Confirmed image records: {len(confirmed_df)}"
)

print(
    f"Rejected/non-confirmed records: "
    f"{len(image_df) - len(confirmed_df)}"
)

# ============================================================================
# CHECK DUPLICATE IMAGES
# ============================================================================

if "image_name" in confirmed_df.columns:

    duplicate_images = confirmed_df[
        confirmed_df["image_name"].duplicated(
            keep=False
        )
    ]

    print(
        f"Duplicate confirmed image records: "
        f"{len(duplicate_images)}"
    )

else:

    print(
        "WARNING: image_name column not found."
    )

# ============================================================================
# LOAD STEP 6 EMBEDDINGS
# ============================================================================

print("\n[2] Loading Step 6 satellite embeddings...")

embeddings = np.load(
    EMBEDDING_FILE
)

print(
    f"Embedding shape: {embeddings.shape}"
)

print(
    f"Embedding dtype: {embeddings.dtype}"
)

# ============================================================================
# VERIFY EMBEDDING SHAPE
# ============================================================================

if embeddings.ndim != 2:

    raise ValueError(
        f"Expected 2-D embeddings, got shape {embeddings.shape}"
    )

if embeddings.shape[1] != 256:

    raise ValueError(
        f"Expected embedding dimension 256, "
        f"got {embeddings.shape[1]}"
    )

print("✓ Embedding dimension = 256")

# ============================================================================
# LOAD TRUSTED SATELLITE FIELDS
# ============================================================================

print("\n[3] Loading trusted satellite fields...")

sat_fields = pd.read_csv(
    SATELLITE_FIELD_FILE
)

print(
    f"Trusted satellite field records: "
    f"{len(sat_fields)}"
)

# ============================================================================
# DETERMINE FIELD ID COLUMN
# ============================================================================

field_id_candidates = [
    "field_id",
    "clean_field_id",
    "satellite_field_id"
]

sat_field_id_col = None

for col in field_id_candidates:

    if col in sat_fields.columns:

        sat_field_id_col = col
        break

if sat_field_id_col is None:

    raise ValueError(
        "Could not find satellite field ID column.\n"
        f"Available columns: {list(sat_fields.columns)}"
    )

print(
    f"Satellite field ID column: {sat_field_id_col}"
)

# ============================================================================
# LOAD SENTINEL TIME SERIES
# ============================================================================

print("\n[4] Loading Sentinel-2 time-series...")

timeseries = pd.read_csv(
    TIMESERIES_FILE
)

print(
    f"Time-series records: {len(timeseries)}"
)

# ============================================================================
# VERIFY 58 FIELDS
# ============================================================================

unique_sat_fields = sorted(
    sat_fields[sat_field_id_col]
    .astype(str)
    .unique()
)

unique_embedding_fields = [
    f"FIELD_{i:02d}"
    for i in range(1, embeddings.shape[0] + 1)
]

print(
    f"Trusted satellite unique fields: "
    f"{len(unique_sat_fields)}"
)

print(
    f"Embedding field slots: "
    f"{len(unique_embedding_fields)}"
)

if len(unique_embedding_fields) != 58:

    raise ValueError(
        "Expected 58 satellite embeddings."
    )

# ============================================================================
# CREATE FIELD → EMBEDDING INDEX
# ============================================================================
#
# Verified Step 6 order:
#
# FIELD_01 → embedding[0]
# FIELD_02 → embedding[1]
# ...
# FIELD_58 → embedding[57]
#
# ============================================================================

field_to_embedding_index = {
    f"FIELD_{i:02d}": i
    for i in range(1, 59)
}

# ============================================================================
# VERIFY ALL MAPPED SATELLITE FIELDS EXIST
# ============================================================================

mapped_satellite_fields = sorted(
    confirmed_df[
        "nearest_satellite_field"
    ]
    .astype(str)
    .unique()
)

print("\nMapped trusted satellite fields:")
print(
    mapped_satellite_fields
)

missing_embedding_fields = [
    field
    for field in mapped_satellite_fields
    if field not in field_to_embedding_index
]

if missing_embedding_fields:

    raise ValueError(
        "Some satellite fields do not have Step 6 embeddings:\n"
        + str(missing_embedding_fields)
    )

print(
    "✓ Every confirmed satellite field has a Step 6 embedding."
)

# ============================================================================
# ADD EMBEDDING INDEX
# ============================================================================

confirmed_df[
    "satellite_embedding_index"
] = confirmed_df[
    "nearest_satellite_field"
].map(
    field_to_embedding_index
)

# ============================================================================
# ADD EMBEDDING DIMENSION
# ============================================================================

confirmed_df[
    "satellite_embedding_dimension"
] = 256

# ============================================================================
# ADD EMBEDDING VECTOR
# ============================================================================

confirmed_df[
    "satellite_embedding"
] = confirmed_df[
    "satellite_embedding_index"
].apply(
    lambda idx: embeddings[int(idx)].tolist()
)

# ============================================================================
# FIELD-LEVEL SUMMARY
# ============================================================================

field_summary = (
    confirmed_df
    .groupby(
        [
            "gps_field_id",
            "nearest_satellite_field"
        ]
    )
    .agg(
        image_count=(
            "gps_field_id",
            "size"
        ),
        min_distance_km=(
            "distance_km",
            "min"
        ),
        max_distance_km=(
            "distance_km",
            "max"
        )
    )
    .reset_index()
)

# ============================================================================
# SAVE FINAL MAPPING
# ============================================================================

confirmed_df.to_csv(
    FINAL_MAPPING_FILE,
    index=False
)

print(
    f"\nSaved final mapping:\n"
    f"{FINAL_MAPPING_FILE}"
)

# ============================================================================
# SAVE EMBEDDING MATRIX FOR CONFIRMED IMAGES
# ============================================================================

image_embedding_matrix = np.vstack(
    confirmed_df[
        "satellite_embedding_index"
    ]
    .apply(
        lambda idx: embeddings[int(idx)]
    )
    .values
)

print(
    f"\nFinal image satellite embedding matrix:"
)

print(
    f"Shape: {image_embedding_matrix.shape}"
)

np.save(
    FINAL_EMBEDDING_FILE,
    image_embedding_matrix
)

print(
    f"Saved:\n{FINAL_EMBEDDING_FILE}"
)

# ============================================================================
# CREATE CLEAN IMAGE → EMBEDDING INDEX TABLE
# ============================================================================

index_columns = [
    "gps_field_id",
    "nearest_satellite_field",
    "satellite_embedding_index",
    "distance_km"
]

if "image_name" in confirmed_df.columns:

    index_columns.insert(
        0,
        "image_name"
    )

if "latitude" in confirmed_df.columns:

    index_columns.extend(
        [
            "latitude",
            "longitude"
        ]
    )

image_index_df = confirmed_df[
    [
        col
        for col in index_columns
        if col in confirmed_df.columns
    ]
].copy()

image_index_df.to_csv(
    IMAGE_EMBEDDING_INDEX_FILE,
    index=False
)

# ============================================================================
# SUMMARY
# ============================================================================

summary_rows = []

for satellite_field, group in confirmed_df.groupby(
    "nearest_satellite_field"
):

    embedding_index = field_to_embedding_index[
        satellite_field
    ]

    summary_rows.append({

        "satellite_field":
            satellite_field,

        "embedding_index":
            embedding_index,

        "embedding_dimension":
            256,

        "image_count":
            len(group),

        "min_distance_km":
            group["distance_km"].min(),

        "max_distance_km":
            group["distance_km"].max()

    })

summary_df = pd.DataFrame(
    summary_rows
)

summary_df = summary_df.sort_values(
    "embedding_index"
)

summary_df.to_csv(
    SUMMARY_FILE,
    index=False
)

# ============================================================================
# VERIFICATION
# ============================================================================

print("\n" + "=" * 80)
print("FINAL STEP 7 VERIFICATION")
print("=" * 80)

# --------------------------------------------------------------------------
# 1. IMAGE COUNT
# --------------------------------------------------------------------------

print(
    f"\n[1] Confirmed images: "
    f"{len(confirmed_df)}"
)

# --------------------------------------------------------------------------
# 2. UNIQUE GPS FIELDS
# --------------------------------------------------------------------------

print(
    f"[2] Unique confirmed GPS fields: "
    f"{confirmed_df['gps_field_id'].nunique()}"
)

# --------------------------------------------------------------------------
# 3. UNIQUE SATELLITE FIELDS
# --------------------------------------------------------------------------

print(
    f"[3] Unique satellite fields used: "
    f"{confirmed_df['nearest_satellite_field'].nunique()}"
)

# --------------------------------------------------------------------------
# 4. EMBEDDING MATRIX
# --------------------------------------------------------------------------

print(
    f"[4] Final embedding matrix shape: "
    f"{image_embedding_matrix.shape}"
)

# --------------------------------------------------------------------------
# 5. NaN
# --------------------------------------------------------------------------

print(
    f"[5] NaN values: "
    f"{np.isnan(image_embedding_matrix).sum()}"
)

# --------------------------------------------------------------------------
# 6. INF
# --------------------------------------------------------------------------

print(
    f"[6] Infinite values: "
    f"{np.isinf(image_embedding_matrix).sum()}"
)

# --------------------------------------------------------------------------
# 7. DISTANCE
# --------------------------------------------------------------------------

print(
    f"[7] Maximum GPS → satellite distance: "
    f"{confirmed_df['distance_km'].max():.6f} km"
)

# --------------------------------------------------------------------------
# 8. EMBEDDING INDEX RANGE
# --------------------------------------------------------------------------

print(
    f"[8] Minimum embedding index: "
    f"{confirmed_df['satellite_embedding_index'].min()}"
)

print(
    f"[9] Maximum embedding index: "
    f"{confirmed_df['satellite_embedding_index'].max()}"
)

# --------------------------------------------------------------------------
# 9. FIELD → EMBEDDING MAPPING
# --------------------------------------------------------------------------

print("\n[10] FIELD → EMBEDDING INDEX")

for field in sorted(
    mapped_satellite_fields,
    key=lambda x: field_to_embedding_index[x]
):

    idx = field_to_embedding_index[field]

    count = (
        confirmed_df[
            confirmed_df[
                "nearest_satellite_field"
            ] == field
        ]
        .shape[0]
    )

    print(
        f"{field} → embedding[{idx}] → "
        f"{count} images"
    )

# ============================================================================
# CHECK EMBEDDING CONSISTENCY
# ============================================================================

print("\n[11] Checking embedding consistency...")

consistency_ok = True

for _, row in confirmed_df.iterrows():

    idx = int(
        row["satellite_embedding_index"]
    )

    stored_vector = np.array(
        row["satellite_embedding"],
        dtype=np.float32
    )

    original_vector = embeddings[idx]

    if not np.allclose(
        stored_vector,
        original_vector,
        atol=1e-6
    ):

        consistency_ok = False

        print(
            "Mismatch found for:",
            row.get(
                "image_name",
                row["gps_field_id"]
            )
        )

        break

print(
    f"Embedding consistency: "
    f"{'PASS' if consistency_ok else 'FAIL'}"
)

# ============================================================================
# WRITE VERIFICATION REPORT
# ============================================================================

with open(
    VERIFICATION_FILE,
    "w"
) as f:

    f.write(
        "STEP 7 — FINAL IMAGE FIELD SATELLITE MAPPING VERIFICATION\n"
    )

    f.write("=" * 70 + "\n\n")

    f.write(
        f"Confirmed image records: {len(confirmed_df)}\n"
    )

    f.write(
        f"Unique GPS fields: "
        f"{confirmed_df['gps_field_id'].nunique()}\n"
    )

    f.write(
        f"Unique satellite fields: "
        f"{confirmed_df['nearest_satellite_field'].nunique()}\n"
    )

    f.write(
        f"Final embedding matrix shape: "
        f"{image_embedding_matrix.shape}\n"
    )

    f.write(
        f"NaN values: "
        f"{np.isnan(image_embedding_matrix).sum()}\n"
    )

    f.write(
        f"Infinite values: "
        f"{np.isinf(image_embedding_matrix).sum()}\n"
    )

    f.write(
        f"Maximum mapping distance: "
        f"{confirmed_df['distance_km'].max():.6f} km\n"
    )

    f.write(
        f"Embedding consistency: "
        f"{'PASS' if consistency_ok else 'FAIL'}\n"
    )

    f.write("\nFIELD → EMBEDDING INDEX\n")

    for field in sorted(
        mapped_satellite_fields,
        key=lambda x: field_to_embedding_index[x]
    ):

        idx = field_to_embedding_index[field]

        f.write(
            f"{field} → embedding[{idx}]\n"
        )

# ============================================================================
# FINAL OUTPUT
# ============================================================================

print("\n" + "=" * 80)
print("STEP 7 COMPLETE")
print("=" * 80)

print(
    "\nFinal mapping:"
)

print(
    FINAL_MAPPING_FILE
)

print(
    "\nFinal image satellite embeddings:"
)

print(
    FINAL_EMBEDDING_FILE
)

print(
    "\nImage embedding index:"
)

print(
    IMAGE_EMBEDDING_INDEX_FILE
)

print(
    "\nVerification:"
)

print(
    VERIFICATION_FILE
)

print(
    "\nSummary:"
)

print(
    SUMMARY_FILE
)

print("\n" + "=" * 80)
print("DO NOT START MULTIMODAL TRAINING YET")
print("=" * 80)

print("""
First verify:

1. Confirmed image count
2. Unique satellite field count
3. Embedding matrix shape
4. NaN / Inf = 0
5. Maximum mapping distance
6. Embedding consistency = PASS

After this verification, we can prepare the final
image embedding + satellite embedding + disease label dataset.
""")

print("=" * 80)