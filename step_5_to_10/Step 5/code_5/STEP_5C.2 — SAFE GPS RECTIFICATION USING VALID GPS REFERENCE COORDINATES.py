# ============================================================================
# STEP 5C.2 — SAFE GPS RECTIFICATION USING VALID GPS REFERENCE COORDINATES
# ============================================================================
# IMPORTANT:
# - Original GPS file is NOT modified.
# - Existing RECTIFIED file is NOT used as input.
# - Only original image_gps_coordinates.csv is used.
# - Suspicious coordinates are corrected only when a strong valid reference
#   coordinate exists.
# ============================================================================

import pandas as pd
import numpy as np
import os
from math import radians, sin, cos, sqrt, atan2

# --------------------------------------------------------------------------
# PATHS
# --------------------------------------------------------------------------

STEP5_DIR = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

ORIGINAL_FILE = os.path.join(
    STEP5_DIR,
    "image_gps_coordinates.csv"
)

OUTPUT_FILE = os.path.join(
    STEP5_DIR,
    "gps_safe_rectification_candidates.csv"
)

REPORT_FILE = os.path.join(
    STEP5_DIR,
    "gps_safe_rectification_report.csv"
)

# --------------------------------------------------------------------------
# LOAD ORIGINAL GPS
# --------------------------------------------------------------------------

df = pd.read_csv(ORIGINAL_FILE)

print("=" * 78)
print("STEP 5C.2 — SAFE GPS RECTIFICATION")
print("=" * 78)

print(f"\nOriginal records: {len(df)}")

# --------------------------------------------------------------------------
# CHECK REQUIRED COLUMNS
# --------------------------------------------------------------------------

required_cols = ["latitude", "longitude"]

for col in required_cols:
    if col not in df.columns:
        raise ValueError(
            f"Required column '{col}' not found.\n"
            f"Available columns: {list(df.columns)}"
        )

# Convert numeric
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

gps_df = df[
    df["latitude"].notna() &
    df["longitude"].notna()
].copy()

print(f"Records with GPS: {len(gps_df)}")

# --------------------------------------------------------------------------
# PROJECT REGION
# --------------------------------------------------------------------------
# Conservative region based on the trusted project GPS distribution.

LAT_MIN = 12.0
LAT_MAX = 15.0
LON_MIN = 78.0
LON_MAX = 81.0

# --------------------------------------------------------------------------
# HAVERSINE DISTANCE
# --------------------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):

    R = 6371.0

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


# --------------------------------------------------------------------------
# BUILD VALID REFERENCE COORDINATES
# --------------------------------------------------------------------------
# A coordinate is treated as a reference only when it is:
# 1. Inside the project region
# 2. NOT one of the known suspicious repeated OCR patterns
#
# We use frequency to identify coordinates that occur repeatedly and are
# therefore more reliable than isolated OCR values.
# --------------------------------------------------------------------------

valid_region = gps_df[
    (gps_df["latitude"] >= LAT_MIN) &
    (gps_df["latitude"] <= LAT_MAX) &
    (gps_df["longitude"] >= LON_MIN) &
    (gps_df["longitude"] <= LON_MAX)
].copy()

coord_counts = (
    valid_region
    .groupby(["latitude", "longitude"])
    .size()
    .reset_index(name="count")
)

print(f"Unique in-region coordinates: {len(coord_counts)}")

# --------------------------------------------------------------------------
# SUSPICIOUS OCR PATTERNS
# --------------------------------------------------------------------------
# These are patterns already identified during your GPS diagnostic.
# They must NOT be used as reference coordinates.

SUSPICIOUS_COORDS = {
    (14.826672, 77.046581),
    (16.826784, 82.046685),
    (14.429626, 87.581415),
    (15.429626, 85.581415),
    (14.826628, 77.046526),
    (14.429626, 85.581415),
    (15.429626, 84.581415),
    (14.826784, 77.046685),
    (15.429626, 86.581415),
    (15.429626, 83.581415),
    (13.434728, 72.570200),
    (14.429626, 81.581415),
}

# Remove suspicious references
reference_df = coord_counts[
    ~coord_counts.apply(
        lambda r: (
            round(float(r["latitude"]), 6),
            round(float(r["longitude"]), 6)
        ) in SUSPICIOUS_COORDS,
        axis=1
    )
].copy()

# Only use coordinates that occur at least twice as references.
# This prevents isolated OCR values becoming "truth".
reference_df = reference_df[
    reference_df["count"] >= 2
].copy()

print(f"Reliable repeated reference coordinates: {len(reference_df)}")

# --------------------------------------------------------------------------
# PRINT TOP REFERENCE COORDINATES
# --------------------------------------------------------------------------

print("\nTop reference coordinates:")
print(
    reference_df
    .sort_values("count", ascending=False)
    .head(20)
    .to_string(index=False)
)

# --------------------------------------------------------------------------
# GENERATE CANDIDATES
# --------------------------------------------------------------------------

results = []

for idx, row in gps_df.iterrows():

    lat = float(row["latitude"])
    lon = float(row["longitude"])

    # --------------------------------------------------------------
    # Already inside project region
    # --------------------------------------------------------------

    inside_region = (
        LAT_MIN <= lat <= LAT_MAX and
        LON_MIN <= lon <= LON_MAX
    )

    if inside_region:

        results.append({
            "original_index": idx,
            "original_latitude": lat,
            "original_longitude": lon,
            "candidate_latitude": lat,
            "candidate_longitude": lon,
            "distance_km": 0.0,
            "reference_count": 0,
            "decision": "UNCHANGED_VALID_REGION",
            "confidence": "VALID"
        })

        continue

    # --------------------------------------------------------------
    # Outside project region
    # --------------------------------------------------------------

    best_distance = float("inf")
    best_lat = np.nan
    best_lon = np.nan
    best_count = 0

    for _, ref in reference_df.iterrows():

        rlat = float(ref["latitude"])
        rlon = float(ref["longitude"])
        rcount = int(ref["count"])

        distance = haversine_km(
            lat,
            lon,
            rlat,
            rlon
        )

        if distance < best_distance:

            best_distance = distance
            best_lat = rlat
            best_lon = rlon
            best_count = rcount

    # --------------------------------------------------------------
    # SAFE DECISION
    # --------------------------------------------------------------
    #
    # We DO NOT automatically correct merely because a candidate exists.
    #
    # Strong correction:
    #   distance <= 5 km AND reference appears >= 5 times
    #
    # Review:
    #   distance <= 20 km AND reference appears >= 2 times
    #
    # Otherwise reject.
    # --------------------------------------------------------------

    if (
        best_distance <= 5.0 and
        best_count >= 5
    ):

        decision = "SAFE_CORRECTION"
        confidence = "HIGH"

    elif (
        best_distance <= 20.0 and
        best_count >= 2
    ):

        decision = "REVIEW"
        confidence = "MEDIUM"

    else:

        decision = "REJECT"
        confidence = "LOW"

    results.append({
        "original_index": idx,
        "original_latitude": lat,
        "original_longitude": lon,
        "candidate_latitude": best_lat,
        "candidate_longitude": best_lon,
        "distance_km": best_distance,
        "reference_count": best_count,
        "decision": decision,
        "confidence": confidence
    })


# --------------------------------------------------------------------------
# RESULTS DATAFRAME
# --------------------------------------------------------------------------

result_df = pd.DataFrame(results)

# --------------------------------------------------------------------------
# ADD IMAGE NAME IF AVAILABLE
# --------------------------------------------------------------------------

if "image_name" in df.columns:

    image_lookup = df[["image_name"]].copy()
    image_lookup["original_index"] = image_lookup.index

    result_df = result_df.merge(
        image_lookup,
        on="original_index",
        how="left"
    )

# --------------------------------------------------------------------------
# SAVE CANDIDATES
# --------------------------------------------------------------------------

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)

# --------------------------------------------------------------------------
# CREATE SUMMARY
# --------------------------------------------------------------------------

summary = (
    result_df["decision"]
    .value_counts()
)

print("\n" + "=" * 78)
print("SAFE RECTIFICATION SUMMARY")
print("=" * 78)

print(summary)

print("\nOutput:")
print(OUTPUT_FILE)

# --------------------------------------------------------------------------
# SHOW ONLY POSSIBLE CORRECTIONS
# --------------------------------------------------------------------------

corrections = result_df[
    result_df["decision"] == "SAFE_CORRECTION"
].copy()

print("\n" + "=" * 78)
print("SAFE CORRECTION CANDIDATES")
print("=" * 78)

print(f"Total safe corrections: {len(corrections)}")

if len(corrections) > 0:

    print(
        corrections[
            [
                "original_latitude",
                "original_longitude",
                "candidate_latitude",
                "candidate_longitude",
                "distance_km",
                "reference_count",
                "confidence"
            ]
        ]
        .sort_values(
            ["reference_count", "distance_km"],
            ascending=[False, True]
        )
        .head(100)
        .to_string(index=False)
    )

# --------------------------------------------------------------------------
# IMPORTANT EXAMPLES
# --------------------------------------------------------------------------

print("\n" + "=" * 78)
print("CHECKING IMPORTANT SUSPICIOUS COORDINATES")
print("=" * 78)

examples = [
    (14.429626, 87.581415),
    (15.429626, 83.581415),
    (18.285594, 79.296834),
    (15.285558, 79.296783),
    (18.433913, 79.578417),
]

for lat, lon in examples:

    matches = result_df[
        np.isclose(result_df["original_latitude"], lat) &
        np.isclose(result_df["original_longitude"], lon)
    ]

    if len(matches) > 0:

        print(
            f"\nOriginal: {lat}, {lon}"
        )

        print(
            matches[
                [
                    "candidate_latitude",
                    "candidate_longitude",
                    "distance_km",
                    "reference_count",
                    "decision",
                    "confidence"
                ]
            ]
            .drop_duplicates()
            .to_string(index=False)
        )

# --------------------------------------------------------------------------
# DO NOT APPLY CORRECTIONS YET
# --------------------------------------------------------------------------

print("\n" + "=" * 78)
print("IMPORTANT")
print("=" * 78)

print("""
NO GPS CORRECTIONS HAVE BEEN APPLIED.

Original file remains untouched:
image_gps_coordinates.csv

Only candidate corrections were generated.

Next step:
1. Inspect SAFE_CORRECTION candidates.
2. Validate them against trusted satellite fields.
3. Only then create the final rectified GPS file.

DO NOT run Step 6 again.
DO NOT run Step 7 yet.
""")

print("=" * 78)