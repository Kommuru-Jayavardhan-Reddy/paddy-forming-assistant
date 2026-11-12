# ============================================================
# STEP 5B — GPS COORDINATE DIAGNOSTIC / RECTIFICATION PRECHECK
# ============================================================

import pandas as pd
import numpy as np
import os

print("=" * 70)
print("STEP 5B — GPS COORDINATE DIAGNOSTIC")
print("=" * 70)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

STEP5_FOLDER = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

INPUT_CSV = os.path.join(
    STEP5_FOLDER,
    "image_gps_coordinates.csv"
)

OUTPUT_CSV = os.path.join(
    STEP5_FOLDER,
    "gps_coordinate_diagnostic.csv"
)

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

df = pd.read_csv(INPUT_CSV)

print("\n[1] INPUT DATA")
print("-" * 70)
print("File:", INPUT_CSV)
print("Total records:", len(df))

print("\nColumns:")
print(df.columns.tolist())

# ------------------------------------------------------------
# FIND LAT/LON COLUMNS
# ------------------------------------------------------------

lat_candidates = [
    "latitude",
    "lat",
    "Latitude",
    "LATITUDE"
]

lon_candidates = [
    "longitude",
    "lon",
    "Longitude",
    "LONGITUDE"
]

lat_col = next((c for c in lat_candidates if c in df.columns), None)
lon_col = next((c for c in lon_candidates if c in df.columns), None)

if lat_col is None or lon_col is None:
    raise ValueError(
        "Latitude / Longitude columns not found."
    )

print("\nLatitude column :", lat_col)
print("Longitude column:", lon_col)

# ------------------------------------------------------------
# NUMERIC CONVERSION
# ------------------------------------------------------------

df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")

# ------------------------------------------------------------
# STATUS CHECK
# ------------------------------------------------------------

if "status" in df.columns:

    gps_df = df[
        df["status"].astype(str).str.upper() == "GPS_FOUND"
    ].copy()

else:

    gps_df = df[
        df[lat_col].notna() &
        df[lon_col].notna()
    ].copy()

print("\n[2] GPS RECORDS")
print("-" * 70)
print("GPS records:", len(gps_df))

# ------------------------------------------------------------
# PROJECT REGION — BROAD INITIAL CHECK
# ------------------------------------------------------------

# Broad India/project-region envelope.
# This is ONLY for diagnosis, not automatic correction.

LAT_MIN = 8.0
LAT_MAX = 20.5

LON_MIN = 72.0
LON_MAX = 86.0

gps_df["basic_coordinate_status"] = "VALID_RANGE"

outside_mask = (
    (gps_df[lat_col] < LAT_MIN) |
    (gps_df[lat_col] > LAT_MAX) |
    (gps_df[lon_col] < LON_MIN) |
    (gps_df[lon_col] > LON_MAX)
)

gps_df.loc[
    outside_mask,
    "basic_coordinate_status"
] = "OUTSIDE_BROAD_REGION"

# ------------------------------------------------------------
# SUSPICIOUS PATTERNS
# ------------------------------------------------------------

# Coordinates with unusual decimal repetition / suspicious
# longitude values are flagged, NOT changed.

gps_df["diagnostic_status"] = gps_df[
    "basic_coordinate_status"
]

gps_df["diagnostic_reason"] = ""

gps_df.loc[
    outside_mask,
    "diagnostic_reason"
] = "Outside broad India/project coordinate range"

# ------------------------------------------------------------
# PROJECT-AREA CHECK
# ------------------------------------------------------------

# Your known clean satellite fields are around:
# latitude ~13-14
# longitude ~79
#
# We use this only to flag points that are far from the
# established project region.

PROJECT_LAT_MIN = 12.0
PROJECT_LAT_MAX = 15.0

PROJECT_LON_MIN = 78.0
PROJECT_LON_MAX = 81.0

project_outside = (
    (gps_df[lat_col] < PROJECT_LAT_MIN) |
    (gps_df[lat_col] > PROJECT_LAT_MAX) |
    (gps_df[lon_col] < PROJECT_LON_MIN) |
    (gps_df[lon_col] > PROJECT_LON_MAX)
)

gps_df.loc[
    project_outside &
    (~outside_mask),
    "diagnostic_status"
] = "PROJECT_REGION_REVIEW"

gps_df.loc[
    project_outside &
    (~outside_mask),
    "diagnostic_reason"
] = "Outside established project-region envelope"

# ------------------------------------------------------------
# DUPLICATE COORDINATE CHECK
# ------------------------------------------------------------

coord_counts = (
    gps_df
    .groupby([lat_col, lon_col])
    .size()
    .reset_index(name="coordinate_count")
)

gps_df = gps_df.merge(
    coord_counts,
    on=[lat_col, lon_col],
    how="left"
)

# ------------------------------------------------------------
# ROUNDING / OCR PATTERN CHECK
# ------------------------------------------------------------

def decimal_pattern(value):

    if pd.isna(value):
        return ""

    s = f"{float(value):.6f}"

    decimal_part = s.split(".")[1]

    # Repeated same digit
    if len(set(decimal_part)) <= 2:
        return "REPEATED_DECIMAL_PATTERN"

    return ""


gps_df["latitude_pattern"] = gps_df[lat_col].apply(
    decimal_pattern
)

gps_df["longitude_pattern"] = gps_df[lon_col].apply(
    decimal_pattern
)

pattern_mask = (
    (gps_df["latitude_pattern"] != "") |
    (gps_df["longitude_pattern"] != "")
)

gps_df.loc[
    pattern_mask &
    (gps_df["diagnostic_status"] == "VALID_RANGE"),
    "diagnostic_status"
] = "PATTERN_REVIEW"

gps_df.loc[
    pattern_mask &
    (gps_df["diagnostic_status"] == "VALID_RANGE"),
    "diagnostic_reason"
] = "Unusual repeated decimal pattern"

# ------------------------------------------------------------
# FINAL REVIEW STATUS
# ------------------------------------------------------------

gps_df["suggested_latitude"] = gps_df[lat_col]
gps_df["suggested_longitude"] = gps_df[lon_col]

gps_df["repair_status"] = "NO_AUTO_REPAIR"

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n[3] DIAGNOSTIC SUMMARY")
print("-" * 70)

print(
    gps_df["diagnostic_status"]
    .value_counts(dropna=False)
)

print("\nCoordinate duplicates:")
print(
    gps_df["coordinate_count"]
    .value_counts()
    .head(10)
)

# ------------------------------------------------------------
# SUSPICIOUS RECORDS
# ------------------------------------------------------------

review_df = gps_df[
    gps_df["diagnostic_status"] != "VALID_RANGE"
].copy()

print("\n[4] RECORDS REQUIRING REVIEW")
print("-" * 70)

print("Review records:", len(review_df))

display_cols = [
    c for c in [
        "image_name",
        "image_path",
        "status",
        lat_col,
        lon_col,
        "diagnostic_status",
        "diagnostic_reason"
    ]
    if c in review_df.columns
]

if len(review_df) > 0:
    print(
        review_df[display_cols]
        .head(30)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# SAVE DIAGNOSTIC FILE
# ------------------------------------------------------------

gps_df.to_csv(
    OUTPUT_CSV,
    index=False
)

print("\n[5] OUTPUT")
print("-" * 70)
print("Saved diagnostic file:")
print(OUTPUT_CSV)

print("\nIMPORTANT:")
print("Original image_gps_coordinates.csv was NOT modified.")
print("No GPS coordinate was automatically changed.")
print("=" * 70)