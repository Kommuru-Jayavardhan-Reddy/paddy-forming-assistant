# ================================================================
# STEP 7.2 — EXACT FIELD ↔ SEQUENCE ↔ EMBEDDING ORDER VERIFICATION
# ================================================================

import os
import numpy as np
import pandas as pd

BASE = "/content/drive/MyDrive/final year project/Real_world_test"
STEP5 = os.path.join(BASE, "Step 5")
STEP6 = os.path.join(BASE, "Step 6")

print("=" * 80)
print("STEP 7.2 — EXACT FIELD ↔ SEQUENCE ↔ EMBEDDING ORDER VERIFICATION")
print("=" * 80)


# ================================================================
# 1. LOAD DATA
# ================================================================

field_file = os.path.join(
    STEP5,
    "clean_field_candidates_renamed.csv"
)

timeseries_file = os.path.join(
    STEP5,
    "sentinel2_timeseries.csv"
)

sequence_file = os.path.join(
    STEP5,
    "bilstm_sequences.npy"
)

embedding_file = os.path.join(
    STEP6,
    "step6F_final_satellite_embeddings.npy"
)

fields = pd.read_csv(field_file)
ts = pd.read_csv(timeseries_file)
sequences = np.load(sequence_file)
embeddings = np.load(embedding_file)


print("\n[1] SHAPES")
print("-" * 80)

print("Fields              :", fields.shape)
print("Time series         :", ts.shape)
print("BiLSTM sequences    :", sequences.shape)
print("Final embeddings    :", embeddings.shape)


# ================================================================
# 2. RECONSTRUCT EXPECTED SEQUENCES FROM CSV
# ================================================================

print("\n" + "=" * 80)
print("[2] RECONSTRUCTING SEQUENCES FROM SENTINEL CSV")
print("=" * 80)

expected_sequences = []

field_order = fields["field_id"].tolist()

for field_id in field_order:

    field_ts = ts[
        ts["field_id"] == field_id
    ].sort_values("time_step")

    values = field_ts[
        ["NDVI", "NDRE", "GNDVI"]
    ].values.astype(np.float32)

    expected_sequences.append(values)


expected_sequences = np.array(
    expected_sequences,
    dtype=np.float32
)

print("\nExpected sequence shape:",
      expected_sequences.shape)


# ================================================================
# 3. CHECK EXACT NUMERICAL MATCH
# ================================================================

print("\n" + "=" * 80)
print("[3] EXACT SEQUENCE ORDER TEST")
print("=" * 80)

if expected_sequences.shape == sequences.shape:

    difference = np.abs(
        expected_sequences - sequences
    )

    max_difference = difference.max()
    mean_difference = difference.mean()

    print("Maximum absolute difference:",
          max_difference)

    print("Mean absolute difference:",
          mean_difference)

    if np.allclose(
        expected_sequences,
        sequences,
        rtol=1e-5,
        atol=1e-6
    ):

        print("\nRESULT: EXACT ORDER MATCH ✅")
        print(
            "bilstm_sequences.npy follows the same "
            "FIELD_01 → FIELD_02 → ... order."
        )

    else:

        print("\nRESULT: ORDER DOES NOT MATCH ❌")


# ================================================================
# 4. CHECK EVERY SEQUENCE INDIVIDUALLY
# ================================================================

print("\n" + "=" * 80)
print("[4] INDIVIDUAL FIELD ↔ SEQUENCE MATCH")
print("=" * 80)

results = []

for i in range(len(field_order)):

    expected = expected_sequences[i]
    actual = sequences[i]

    max_diff = np.max(
        np.abs(expected - actual)
    )

    mean_diff = np.mean(
        np.abs(expected - actual)
    )

    exact = np.allclose(
        expected,
        actual,
        rtol=1e-5,
        atol=1e-6
    )

    results.append({
        "sequence_index": i,
        "field_id": field_order[i],
        "max_difference": max_diff,
        "mean_difference": mean_diff,
        "match": exact
    })


sequence_check = pd.DataFrame(results)

print(
    sequence_check.to_string(index=False)
)


# ================================================================
# 5. SUMMARY OF SEQUENCE MATCHING
# ================================================================

print("\n" + "=" * 80)
print("[5] SEQUENCE MATCH SUMMARY")
print("=" * 80)

matched = sequence_check["match"].sum()
total = len(sequence_check)

print("Matched:", matched)
print("Total  :", total)

if matched == total:

    print("\n✅ ALL 58 SEQUENCES MATCH EXACTLY")

else:

    print(
        f"\n❌ ONLY {matched}/{total} SEQUENCES MATCH"
    )


# ================================================================
# 6. TEST WHETHER EMBEDDING ORDER FOLLOWS SEQUENCE ORDER
# ================================================================

print("\n" + "=" * 80)
print("[6] EMBEDDING ORDER")
print("=" * 80)

print("""
The final embeddings were generated from the 58 input
satellite sequences.

Step 6 verification confirms:

Input satellite shape  = (58, 10, 3)
Final embedding shape  = (58, 256)
Input/output match     = True

Therefore, if the sequence order is proven as:

sequence[0]  = FIELD_01
sequence[1]  = FIELD_02
...
sequence[57] = FIELD_58

then the corresponding embedding order is:

embedding[0]  = FIELD_01
embedding[1]  = FIELD_02
...
embedding[57] = FIELD_58
""")

if matched == total:

    print("SEQUENCE ORDER: PROVEN ✅")

    print("\nTherefore the embedding mapping is:")

    for i in range(min(10, len(field_order))):

        print(
            f"embedding[{i}] → {field_order[i]}"
        )

    print("...")
    print(
        f"embedding[57] → {field_order[57]}"
    )

else:

    print(
        "SEQUENCE ORDER: NOT PROVEN ❌"
    )


# ================================================================
# 7. CREATE VERIFIED FIELD ↔ EMBEDDING MAP
# ================================================================

print("\n" + "=" * 80)
print("[7] VERIFIED MAPPING")
print("=" * 80)

if matched == total:

    verified_mapping = fields[
        [
            "field_id",
            "clean_field_id",
            "latitude",
            "longitude",
            "sentinel2_image_count"
        ]
    ].copy()

    verified_mapping.insert(
        0,
        "embedding_index",
        np.arange(len(fields))
    )

    verified_mapping.insert(
        1,
        "sequence_index",
        np.arange(len(fields))
    )

    print(
        verified_mapping.to_string(index=False)
    )

else:

    print(
        "Mapping NOT created because sequence order "
        "has not been proven."
    )


# ================================================================
# 8. FINAL DECISION
# ================================================================

print("\n" + "=" * 80)
print("FINAL DECISION")
print("=" * 80)

if matched == total:

    print("""
✅ MAPPING PROBLEM SOLVED

Proven chain:

FIELD
  ↓
Sentinel-2 time series
  ↓
BiLSTM sequence
  ↓
256-D satellite embedding

Order:

FIELD_01 → sequence[0] → embedding[0]
FIELD_02 → sequence[1] → embedding[1]
...
FIELD_58 → sequence[57] → embedding[57]

Now we can safely connect GPS images to the
correct satellite embedding through field_id.
""")

else:

    print("""
❌ MAPPING PROBLEM NOT SOLVED YET

The BiLSTM sequence order does not exactly match
the FIELD order.

Do NOT continue to Step 7 pairing.

We need to recover the actual sequence ordering first.
""")


print("=" * 80)
print("END")
print("=" * 80)