# ============================================================
# STEP 5B.4 — REPEATED GPS CORRUPTION PATTERN ANALYSIS
# ============================================================

import pandas as pd
import numpy as np
import os

print("=" * 75)
print("STEP 5B.4 — REPEATED GPS CORRUPTION ANALYSIS")
print("=" * 75)

STEP5_FOLDER = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

GPS_FILE = os.path.join(
    STEP5_FOLDER,
    "image_gps_coordinates.csv"
)

OUTPUT_FILE = os.path.join(
    STEP5_FOLDER,
    "gps_repeated_coordinate_patterns.csv"
)

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

df = pd.read_csv(GPS_FILE)

df["latitude"] = pd.to_numeric(
    df["latitude"], errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"], errors="coerce"
)

df = df[
    (df["status"].astype(str).str.upper() == "GPS_FOUND") &
    df["latitude"].notna() &
    df["longitude"].notna()
].copy()

print("\nGPS records:", len(df))

# ------------------------------------------------------------
# ROUND COORDINATES
# ------------------------------------------------------------

df["lat_round"] = df["latitude"].round(6)
df["lon_round"] = df["longitude"].round(6)

# ------------------------------------------------------------
# COUNT EXACT COORDINATE REPEATS
# ------------------------------------------------------------

coord_groups = (
    df.groupby(
        ["lat_round", "lon_round"],
        as_index=False
    )
    .agg(
        image_count=("image_name", "count"),
        image_names=("image_name", list),
        image_paths=("image_path", list)
    )
    .sort_values(
        "image_count",
        ascending=False
    )
)

print("\n" + "=" * 75)
print("MOST REPEATED GPS COORDINATES")
print("=" * 75)

print(
    coord_groups[
        [
            "lat_round",
            "lon_round",
            "image_count"
        ]
    ]
    .head(40)
    .to_string(index=False)
)

# ------------------------------------------------------------
# PROJECT REGION
# ------------------------------------------------------------

PROJECT_LAT_MIN = 12.0
PROJECT_LAT_MAX = 15.0

PROJECT_LON_MIN = 78.0
PROJECT_LON_MAX = 81.0

coord_groups["inside_project_region"] = (
    (coord_groups["lat_round"] >= PROJECT_LAT_MIN) &
    (coord_groups["lat_round"] <= PROJECT_LAT_MAX) &
    (coord_groups["lon_round"] >= PROJECT_LON_MIN) &
    (coord_groups["lon_round"] <= PROJECT_LON_MAX)
)

# ------------------------------------------------------------
# SUSPICIOUS REPEATED COORDINATES
# ------------------------------------------------------------

suspicious = coord_groups[
    (~coord_groups["inside_project_region"]) &
    (coord_groups["image_count"] >= 2)
].copy()

print("\n" + "=" * 75)
print("REPEATED SUSPICIOUS COORDINATES")
print("=" * 75)

print(
    "Repeated suspicious coordinate groups:",
    len(suspicious)
)

if len(suspicious) > 0:

    print(
        suspicious[
            [
                "lat_round",
                "lon_round",
                "image_count"
            ]
        ]
        .head(50)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

suspicious.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 75)
print("OUTPUT")
print("=" * 75)

print(
    "Saved:",
    OUTPUT_FILE
)

print("\nOriginal GPS CSV was NOT modified.")

print("\nNEXT:")
print(
    "We will use these repeated patterns to determine "
    "whether the OCR coordinates can be safely repaired."
)

print("=" * 75)