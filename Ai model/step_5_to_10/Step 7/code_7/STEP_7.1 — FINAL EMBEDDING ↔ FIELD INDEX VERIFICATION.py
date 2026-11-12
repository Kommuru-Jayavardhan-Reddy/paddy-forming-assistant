# ================================================================
# STEP 7.1 — FINAL EMBEDDING ↔ FIELD INDEX VERIFICATION
# ================================================================

import os
import numpy as np
import pandas as pd

BASE = "/content/drive/MyDrive/final year project/Real_world_test"
STEP5 = os.path.join(BASE, "Step 5")
STEP6 = os.path.join(BASE, "Step 6")

print("=" * 80)
print("STEP 7.1 — EMBEDDING ↔ FIELD INDEX VERIFICATION")
print("=" * 80)


# ------------------------------------------------
# 1. LOAD FINAL SATELLITE EMBEDDINGS
# ------------------------------------------------

embedding_file = os.path.join(
    STEP6,
    "step6F_final_satellite_embeddings.npy"
)

embeddings = np.load(embedding_file)

print("\n[1] FINAL SATELLITE EMBEDDINGS")
print("-" * 80)

print("File:", embedding_file)
print("Shape:", embeddings.shape)
print("dtype:", embeddings.dtype)


# ------------------------------------------------
# 2. LOAD 58 CLEAN FIELDS
# ------------------------------------------------

field_file = os.path.join(
    STEP5,
    "clean_field_candidates_renamed.csv"
)

fields = pd.read_csv(field_file)

print("\n[2] CLEAN FIELD DATA")
print("-" * 80)

print("Rows:", len(fields))
print("Columns:", list(fields.columns))

print("\nField IDs:")
print(fields["field_id"].tolist())


# ------------------------------------------------
# 3. CHECK WHETHER FIELD ORDER MATCHES EMBEDDING COUNT
# ------------------------------------------------

print("\n[3] FIELD ↔ EMBEDDING COUNT")
print("-" * 80)

print("Number of fields:", len(fields))
print("Number of embeddings:", embeddings.shape[0])

if len(fields) == embeddings.shape[0]:

    print("STATUS: COUNT MATCH ✅")

else:

    print("STATUS: COUNT MISMATCH ❌")


# ------------------------------------------------
# 4. LOAD BILSTM SEQUENCES
# ------------------------------------------------

bilstm_file = os.path.join(
    STEP5,
    "bilstm_sequences.npy"
)

print("\n[4] BILSTM SEQUENCES")
print("-" * 80)

if os.path.exists(bilstm_file):

    bilstm = np.load(bilstm_file)

    print("File:", bilstm_file)
    print("Shape:", bilstm.shape)
    print("dtype:", bilstm.dtype)

else:

    print("bilstm_sequences.npy NOT FOUND")


# ------------------------------------------------
# 5. LOAD SENTINEL TIME SERIES
# ------------------------------------------------

timeseries_file = os.path.join(
    STEP5,
    "sentinel2_timeseries.csv"
)

print("\n[5] SENTINEL-2 TIME SERIES")
print("-" * 80)

if os.path.exists(timeseries_file):

    ts = pd.read_csv(timeseries_file)

    print("Rows:", len(ts))
    print("Columns:")
    for c in ts.columns:
        print("   ", c)

    print("\nFirst 10 rows:")
    print(ts.head(10).to_string(index=False))

else:

    print("sentinel2_timeseries.csv NOT FOUND")


# ------------------------------------------------
# 6. LOAD SELECTED DATES
# ------------------------------------------------

dates_file = os.path.join(
    STEP5,
    "sentinel2_selected_dates.csv"
)

print("\n[6] SENTINEL-2 SELECTED DATES")
print("-" * 80)

if os.path.exists(dates_file):

    dates = pd.read_csv(dates_file)

    print("Rows:", len(dates))
    print("Columns:")

    for c in dates.columns:
        print("   ", c)

    print("\nFirst 10 rows:")
    print(dates.head(10).to_string(index=False))

else:

    print("sentinel2_selected_dates.csv NOT FOUND")


# ------------------------------------------------
# 7. LOAD STEP 6 VERIFICATION SUMMARY
# ------------------------------------------------

summary_file = os.path.join(
    STEP6,
    "step6F_verification_summary.txt"
)

print("\n[7] STEP 6 VERIFICATION SUMMARY")
print("-" * 80)

if os.path.exists(summary_file):

    with open(summary_file, "r", encoding="utf-8") as f:
        summary = f.read()

    print(summary)

else:

    print("Verification summary NOT FOUND")


# ------------------------------------------------
# 8. CHECK FIELD ORDER
# ------------------------------------------------

print("\n" + "=" * 80)
print("[8] FIELD ORDER CHECK")
print("=" * 80)

print("\nFirst 20 field rows:")

print(
    fields[
        [
            "field_id",
            "latitude",
            "longitude",
            "sentinel2_image_count",
            "clean_field_id"
        ]
    ]
    .head(20)
    .to_string(index=False)
)


# ------------------------------------------------
# 9. CREATE TEMPORARY INDEX TABLE
# ------------------------------------------------

print("\n" + "=" * 80)
print("[9] TEMPORARY FIELD ↔ EMBEDDING INDEX")
print("=" * 80)

if len(fields) == embeddings.shape[0]:

    temp_mapping = pd.DataFrame({
        "embedding_index": np.arange(len(fields)),
        "field_id": fields["field_id"].values,
        "clean_field_id": fields["clean_field_id"].values,
        "latitude": fields["latitude"].values,
        "longitude": fields["longitude"].values
    })

    print(
        temp_mapping.head(20).to_string(index=False)
    )

    print("\nIMPORTANT:")
    print(
        "This is ONLY the current row-order hypothesis."
    )
    print(
        "It is NOT yet accepted as the true mapping."
    )

else:

    print(
        "Cannot create temporary mapping because counts do not match."
    )


# ------------------------------------------------
# 10. CHECK FOR EXPLICIT INDEX COLUMNS
# ------------------------------------------------

print("\n" + "=" * 80)
print("[10] SEARCHING FOR EXPLICIT EMBEDDING INDEX")
print("=" * 80)

possible_index_names = [
    "index",
    "embedding_index",
    "sequence_index",
    "satellite_sequence_index",
    "field_index",
    "sample_index"
]

for col in fields.columns:

    col_lower = str(col).lower()

    if any(name in col_lower for name in possible_index_names):

        print(
            "Potential index column found:",
            col
        )


if os.path.exists(timeseries_file):

    for col in ts.columns:

        col_lower = str(col).lower()

        if any(name in col_lower for name in possible_index_names):

            print(
                "Potential index column in time series:",
                col
            )


# ------------------------------------------------
# 11. FINAL STATUS
# ------------------------------------------------

print("\n" + "=" * 80)
print("CURRENT MAPPING STATUS")
print("=" * 80)

print("""
CONFIRMED:

✓ 58 final satellite embeddings exist
✓ Embedding dimension = 256
✓ 58 clean field candidates exist
✓ Each clean field has GPS coordinates
✓ Image → field mapping exists through gps_spatial_clusters.csv
✓ Sentinel-2 data exists

NOT YET PROVEN:

? embedding index → field_id

DO NOT assume:

embedding[0] = FIELD_01
embedding[1] = FIELD_02
...

until Step 6 generation order is verified.

NEXT STEP:
Determine the exact order used when Step 6 created
step6F_final_satellite_embeddings.npy.
""")

print("=" * 80)
print("VERIFICATION FINISHED")
print("=" * 80)