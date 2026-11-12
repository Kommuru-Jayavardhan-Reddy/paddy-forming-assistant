# ============================================================
# STEP 5C.1 — GPS FIELD → TRUSTED SATELLITE FIELD VALIDATION
# ============================================================

import pandas as pd
import numpy as np
import os
from math import radians, sin, cos, sqrt, atan2

print("=" * 75)
print("STEP 5C.1 — GPS FIELD TO SATELLITE FIELD VALIDATION")
print("=" * 75)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

STEP5 = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

GPS_CLUSTER_FILE = os.path.join(
    STEP5,
    "gps_spatial_clusters_RECTIFIED.csv"
)

CLEAN_FIELD_FILE = os.path.join(
    STEP5,
    "clean_field_candidates_renamed.csv"
)

OUTPUT_FILE = os.path.join(
    STEP5,
    "gps_to_satellite_field_validation.csv"
)

# ------------------------------------------------------------
# LOAD GPS CLUSTERS
# ------------------------------------------------------------

gps = pd.read_csv(GPS_CLUSTER_FILE)

gps = gps[
    gps["field_id"].notna() &
    (gps["field_id"] != "NOISE")
].copy()

print("\nGPS field records:", len(gps))
print("Unique GPS fields:", gps["field_id"].nunique())

# ------------------------------------------------------------
# CREATE GPS FIELD CENTERS
# ------------------------------------------------------------

gps_fields = (
    gps
    .groupby("field_id", as_index=False)
    .agg(
        gps_image_count=("image_name", "count"),
        gps_latitude=("latitude", "mean"),
        gps_longitude=("longitude", "mean"),
        rectified_image_count=(
            "gps_correction_status",
            lambda x: (
                x.astype(str)
                .str.upper()
                .eq("RECTIFIED_HIGH_CONFIDENCE")
                .sum()
            )
        )
    )
)

print(
    "GPS field centers:",
    len(gps_fields)
)

# ------------------------------------------------------------
# LOAD TRUSTED 58 SATELLITE FIELDS
# ------------------------------------------------------------

sat = pd.read_csv(
    CLEAN_FIELD_FILE
)

sat["latitude"] = pd.to_numeric(
    sat["latitude"],
    errors="coerce"
)

sat["longitude"] = pd.to_numeric(
    sat["longitude"],
    errors="coerce"
)

sat = sat[
    sat["latitude"].notna() &
    sat["longitude"].notna()
].copy()

print(
    "Trusted satellite fields:",
    len(sat)
)

# ------------------------------------------------------------
# HAVERSINE
# ------------------------------------------------------------

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

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

    return (
        2
        * R
        * atan2(
            sqrt(a),
            sqrt(1 - a)
        )
    )

# ------------------------------------------------------------
# FIND NEAREST SATELLITE FIELD
# ------------------------------------------------------------

results = []

for _, gps_row in gps_fields.iterrows():

    gps_field = gps_row["field_id"]

    gps_lat = float(
        gps_row["gps_latitude"]
    )

    gps_lon = float(
        gps_row["gps_longitude"]
    )

    distances = []

    for _, sat_row in sat.iterrows():

        distance = haversine_km(
            gps_lat,
            gps_lon,
            float(sat_row["latitude"]),
            float(sat_row["longitude"])
        )

        distances.append(distance)

    distances = np.array(distances)

    order = np.argsort(distances)

    best_idx = order[0]

    best_distance = distances[best_idx]

    best_sat = sat.iloc[best_idx]

    # Second nearest
    if len(order) > 1:

        second_idx = order[1]

        second_distance = distances[second_idx]

        second_sat = sat.iloc[second_idx]

    else:

        second_distance = np.nan
        second_sat = None

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    # <= 0.5 km = strong spatial match
    # 0.5–2 km = review
    # > 2 km = reject

    if best_distance <= 0.5:

        decision = "ACCEPT"

    elif best_distance <= 2.0:

        decision = "REVIEW"

    else:

        decision = "REJECT"

    results.append({

        "gps_field_id":
            gps_field,

        "gps_image_count":
            int(gps_row["gps_image_count"]),

        "rectified_image_count":
            int(gps_row["rectified_image_count"]),

        "gps_latitude":
            round(gps_lat, 6),

        "gps_longitude":
            round(gps_lon, 6),

        "nearest_satellite_field":
            best_sat["field_id"],

        "satellite_latitude":
            round(float(best_sat["latitude"]), 6),

        "satellite_longitude":
            round(float(best_sat["longitude"]), 6),

        "distance_km":
            round(best_distance, 4),

        "distance_m":
            round(best_distance * 1000, 1),

        "second_nearest_field":
            (
                second_sat["field_id"]
                if second_sat is not None
                else ""
            ),

        "second_distance_km":
            round(second_distance, 4)
            if not np.isnan(second_distance)
            else np.nan,

        "decision":
            decision
    })

# ------------------------------------------------------------
# RESULT DATAFRAME
# ------------------------------------------------------------

result = pd.DataFrame(
    results
)

result = result.sort_values(
    "distance_km"
).reset_index(drop=True)

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

result.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("MAPPING VALIDATION SUMMARY")
print("=" * 75)

print(
    result["decision"]
    .value_counts()
)

# ------------------------------------------------------------
# ACCEPTED
# ------------------------------------------------------------

accepted = result[
    result["decision"] == "ACCEPT"
]

print("\n" + "=" * 75)
print("ACCEPTED GPS → SATELLITE MATCHES")
print("=" * 75)

print(
    "Accepted:",
    len(accepted)
)

if len(accepted) > 0:

    print(
        accepted[
            [
                "gps_field_id",
                "gps_image_count",
                "nearest_satellite_field",
                "distance_m",
                "rectified_image_count",
                "decision"
            ]
        ]
        .head(100)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# REVIEW
# ------------------------------------------------------------

review = result[
    result["decision"] == "REVIEW"
]

print("\n" + "=" * 75)
print("REVIEW MATCHES")
print("=" * 75)

print(
    "Review:",
    len(review)
)

if len(review) > 0:

    print(
        review[
            [
                "gps_field_id",
                "gps_image_count",
                "nearest_satellite_field",
                "distance_m",
                "second_nearest_field",
                "second_distance_km",
                "decision"
            ]
        ]
        .head(100)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# REJECTED
# ------------------------------------------------------------

rejected = result[
    result["decision"] == "REJECT"
]

print("\n" + "=" * 75)
print("REJECTED MATCHES")
print("=" * 75)

print(
    "Rejected:",
    len(rejected)
)

if len(rejected) > 0:

    print(
        rejected[
            [
                "gps_field_id",
                "gps_image_count",
                "gps_latitude",
                "gps_longitude",
                "nearest_satellite_field",
                "distance_km",
                "decision"
            ]
        ]
        .head(50)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("OUTPUT SAVED")
print("=" * 75)

print(OUTPUT_FILE)

print("\nIMPORTANT:")
print("No GPS field was automatically merged.")
print("No satellite field was modified.")
print("This file contains validation candidates only.")

print("=" * 75)