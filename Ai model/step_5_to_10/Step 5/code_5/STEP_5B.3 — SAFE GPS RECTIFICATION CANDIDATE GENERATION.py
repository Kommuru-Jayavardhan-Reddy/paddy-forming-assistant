# ============================================================
# STEP 5B.3 — SAFE GPS RECTIFICATION CANDIDATE GENERATION
# ============================================================

import pandas as pd
import numpy as np
import os
from math import radians, sin, cos, sqrt, atan2

print("=" * 75)
print("STEP 5B.3 — SAFE GPS RECTIFICATION")
print("=" * 75)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

STEP5_FOLDER = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

GPS_FILE = os.path.join(
    STEP5_FOLDER,
    "image_gps_coordinates.csv"
)

CLEAN_FIELD_FILE = os.path.join(
    STEP5_FOLDER,
    "clean_field_candidates_renamed.csv"
)

OUTPUT_FILE = os.path.join(
    STEP5_FOLDER,
    "gps_rectification_candidates.csv"
)

# ------------------------------------------------------------
# LOAD GPS DATA
# ------------------------------------------------------------

gps = pd.read_csv(GPS_FILE)

gps["latitude"] = pd.to_numeric(
    gps["latitude"], errors="coerce"
)

gps["longitude"] = pd.to_numeric(
    gps["longitude"], errors="coerce"
)

gps = gps[
    gps["status"].astype(str).str.upper() == "GPS_FOUND"
].copy()

gps = gps[
    gps["latitude"].notna() &
    gps["longitude"].notna()
].copy()

print("\nGPS records:", len(gps))

# ------------------------------------------------------------
# LOAD TRUSTED 58 CLEAN FIELDS
# ------------------------------------------------------------

fields = pd.read_csv(CLEAN_FIELD_FILE)

print("Trusted clean fields:", len(fields))

print("\nClean field columns:")
print(fields.columns.tolist())

# ------------------------------------------------------------
# FIND FIELD ID COLUMN
# ------------------------------------------------------------

field_id_col = None

for c in [
    "field_id",
    "clean_field_id",
    "FIELD_ID",
    "field",
    "Field_ID"
]:
    if c in fields.columns:
        field_id_col = c
        break

if field_id_col is None:
    raise ValueError(
        "Field ID column not found in clean_field_candidates_renamed.csv"
    )

# ------------------------------------------------------------
# MAKE SURE LAT/LON ARE NUMERIC
# ------------------------------------------------------------

fields["latitude"] = pd.to_numeric(
    fields["latitude"], errors="coerce"
)

fields["longitude"] = pd.to_numeric(
    fields["longitude"], errors="coerce"
)

fields = fields[
    fields["latitude"].notna() &
    fields["longitude"].notna()
].copy()

print("Usable trusted fields:", len(fields))

# ------------------------------------------------------------
# HAVERSINE DISTANCE
# ------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):

    R = 6371.0

    lat1 = radians(lat1)
    lat2 = radians(lat2)

    dlat = lat2 - lat1
    dlon = radians(lon2) - radians(lon1)

    a = (
        sin(dlat / 2) ** 2
        +
        cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    return 2 * R * atan2(
        sqrt(a),
        sqrt(1 - a)
    )


# ------------------------------------------------------------
# ESTABLISHED PROJECT REGION
# ------------------------------------------------------------

PROJECT_LAT_MIN = 12.0
PROJECT_LAT_MAX = 15.0

PROJECT_LON_MIN = 78.0
PROJECT_LON_MAX = 81.0


def inside_project_region(lat, lon):

    return (
        PROJECT_LAT_MIN <= lat <= PROJECT_LAT_MAX
        and
        PROJECT_LON_MIN <= lon <= PROJECT_LON_MAX
    )


# ------------------------------------------------------------
# CREATE RECTIFICATION CANDIDATES
# ------------------------------------------------------------

results = []

for _, row in gps.iterrows():

    lat = float(row["latitude"])
    lon = float(row["longitude"])

    # --------------------------------------------------------
    # DISTANCE TO EVERY TRUSTED FIELD
    # --------------------------------------------------------

    distances = []

    for _, field in fields.iterrows():

        d = haversine_km(
            lat,
            lon,
            float(field["latitude"]),
            float(field["longitude"])
        )

        distances.append(d)

    distances = np.array(distances)

    nearest_idx = np.argmin(distances)

    nearest_distance_km = distances[nearest_idx]

    nearest_field = fields.iloc[nearest_idx]

    # Second nearest field
    sorted_distances = np.sort(distances)

    if len(sorted_distances) >= 2:
        second_distance_km = sorted_distances[1]
    else:
        second_distance_km = np.nan

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    original_inside = inside_project_region(
        lat,
        lon
    )

    # Strong candidate:
    # coordinate is outside project region but close to
    # an established trusted field.

    if (
        not original_inside
        and
        nearest_distance_km <= 10
    ):
        status = "CORRECTION_CANDIDATE"

    elif (
        not original_inside
        and
        nearest_distance_km <= 25
    ):
        status = "REVIEW_NEAR_FIELD"

    elif original_inside:
        status = "ALREADY_IN_PROJECT_REGION"

    else:
        status = "REVIEW_FAR_FROM_FIELDS"

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    results.append({

        "image_name": row.get("image_name", ""),

        "image_path": row.get("image_path", ""),

        "original_latitude": lat,

        "original_longitude": lon,

        "original_status": row.get("status", ""),

        "nearest_field": nearest_field[field_id_col],

        "nearest_field_latitude":
            float(nearest_field["latitude"]),

        "nearest_field_longitude":
            float(nearest_field["longitude"]),

        "nearest_field_distance_km":
            round(nearest_distance_km, 4),

        "second_nearest_distance_km":
            round(second_distance_km, 4),

        "inside_project_region":
            original_inside,

        "rectification_status":
            status,

        # IMPORTANT:
        # We are NOT changing coordinates yet.
        "suggested_latitude": np.nan,

        "suggested_longitude": np.nan,

        "repair_distance_km": np.nan
    })


result_df = pd.DataFrame(results)

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("RECTIFICATION CANDIDATE SUMMARY")
print("=" * 75)

print(
    result_df["rectification_status"]
    .value_counts()
)

print("\nNearest-field distance statistics:")
print(
    result_df["nearest_field_distance_km"]
    .describe()
)

# ------------------------------------------------------------
# SHOW IMPORTANT SUSPICIOUS RECORDS
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("POTENTIAL CORRECTION RECORDS")
print("=" * 75)

candidate_df = result_df[
    result_df["rectification_status"] ==
    "CORRECTION_CANDIDATE"
].copy()

print(
    "Correction candidates:",
    len(candidate_df)
)

if len(candidate_df) > 0:

    print(
        candidate_df[
            [
                "image_name",
                "original_latitude",
                "original_longitude",
                "nearest_field",
                "nearest_field_latitude",
                "nearest_field_longitude",
                "nearest_field_distance_km",
                "second_nearest_distance_km",
                "rectification_status"
            ]
        ]
        .head(50)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# SHOW FAR RECORDS
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("FAR / UNSAFE RECORDS")
print("=" * 75)

far_df = result_df[
    result_df["rectification_status"] ==
    "REVIEW_FAR_FROM_FIELDS"
]

print(
    "Far records:",
    len(far_df)
)

if len(far_df) > 0:

    print(
        far_df[
            [
                "image_name",
                "original_latitude",
                "original_longitude",
                "nearest_field",
                "nearest_field_distance_km"
            ]
        ]
        .head(30)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("OUTPUT SAVED")
print("=" * 75)

print(OUTPUT_FILE)

print("\nOriginal GPS file was NOT modified.")
print("No coordinate was automatically changed.")
print("=" * 75)