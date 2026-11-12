# ============================================================
# STEP 5B.8 — FINAL FIELD CLUSTERING USING RECTIFIED GPS
# ============================================================

import pandas as pd
import numpy as np
import os
from sklearn.cluster import DBSCAN

print("=" * 75)
print("STEP 5B.8 — FINAL FIELD CLUSTERING")
print("=" * 75)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

STEP5 = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

INPUT_CSV = os.path.join(
    STEP5,
    "image_gps_coordinates_RECTIFIED.csv"
)

OUTPUT_CSV = os.path.join(
    STEP5,
    "gps_spatial_clusters_RECTIFIED.csv"
)

SUMMARY_CSV = os.path.join(
    STEP5,
    "gps_cluster_summary_RECTIFIED.csv"
)

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

df = pd.read_csv(INPUT_CSV)

df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

print("\nTotal records:", len(df))

# ------------------------------------------------------------
# GPS VALID RECORDS
# ------------------------------------------------------------

gps_df = df[
    (df["status"].astype(str).str.upper() == "GPS_FOUND") &
    df["latitude"].notna() &
    df["longitude"].notna()
].copy()

print("Valid GPS records:", len(gps_df))

# ------------------------------------------------------------
# DBSCAN SETTINGS
# ------------------------------------------------------------

EPS_METERS = 100
MIN_SAMPLES = 2

print("\nDBSCAN settings:")
print("Radius:", EPS_METERS, "meters")
print("Minimum samples:", MIN_SAMPLES)

# ------------------------------------------------------------
# PREPARE COORDINATES
# ------------------------------------------------------------

coords = np.radians(
    gps_df[
        ["latitude", "longitude"]
    ].values
)

EARTH_RADIUS = 6371000.0

eps_radians = (
    EPS_METERS /
    EARTH_RADIUS
)

# ------------------------------------------------------------
# DBSCAN
# ------------------------------------------------------------

dbscan = DBSCAN(
    eps=eps_radians,
    min_samples=MIN_SAMPLES,
    metric="haversine"
)

labels = dbscan.fit_predict(coords)

gps_df["cluster_id"] = labels

# ------------------------------------------------------------
# ASSIGN FIELD IDs
# ------------------------------------------------------------

cluster_ids = sorted(
    [
        x for x in gps_df["cluster_id"].unique()
        if x >= 0
    ]
)

cluster_to_field = {
    cluster_id:
    f"FIELD_{i+1:02d}"
    for i, cluster_id in enumerate(cluster_ids)
}

gps_df["field_id"] = gps_df[
    "cluster_id"
].map(cluster_to_field)

gps_df.loc[
    gps_df["cluster_id"] == -1,
    "field_id"
] = "NOISE"

# ------------------------------------------------------------
# ADD RECTIFICATION INFORMATION
# ------------------------------------------------------------

if "gps_correction_status" not in gps_df.columns:
    gps_df["gps_correction_status"] = "UNKNOWN"

if "gps_correction_score" not in gps_df.columns:
    gps_df["gps_correction_score"] = np.nan

# ------------------------------------------------------------
# SAVE IMAGE-LEVEL CLUSTERS
# ------------------------------------------------------------

gps_df.to_csv(
    OUTPUT_CSV,
    index=False
)

# ------------------------------------------------------------
# CREATE FIELD SUMMARY
# ------------------------------------------------------------

summary_rows = []

for cluster_id in cluster_ids:

    group = gps_df[
        gps_df["cluster_id"] == cluster_id
    ].copy()

    field_id = cluster_to_field[cluster_id]

    center_lat = group["latitude"].mean()
    center_lon = group["longitude"].mean()

    corrected_count = (
        group["gps_correction_status"]
        .astype(str)
        .str.upper()
        .eq("RECTIFIED_HIGH_CONFIDENCE")
        .sum()
    )

    summary_rows.append({

        "field_id": field_id,

        "cluster_id": cluster_id,

        "image_count": len(group),

        "center_latitude":
            round(center_lat, 6),

        "center_longitude":
            round(center_lon, 6),

        "rectified_image_count":
            int(corrected_count),

        "field_quality":
            (
                "STRONG"
                if len(group) >= 10
                else
                "MEDIUM"
                if len(group) >= 5
                else
                "WEAK"
            )
    })

summary = pd.DataFrame(
    summary_rows
)

summary = summary.sort_values(
    "image_count",
    ascending=False
).reset_index(drop=True)

summary.to_csv(
    SUMMARY_CSV,
    index=False
)

# ------------------------------------------------------------
# NOISE
# ------------------------------------------------------------

noise_count = (
    gps_df["cluster_id"] == -1
).sum()

# ------------------------------------------------------------
# FINAL REPORT
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("FINAL CLUSTERING RESULT")
print("=" * 75)

print("GPS records:", len(gps_df))
print("Fields:", len(summary))
print("Noise records:", noise_count)

print(
    "Noise percentage:",
    round(
        noise_count / len(gps_df) * 100,
        2
    ),
    "%"
)

# ------------------------------------------------------------
# FIELD DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("TOP FIELDS")
print("=" * 75)

print(
    summary[
        [
            "field_id",
            "image_count",
            "center_latitude",
            "center_longitude",
            "rectified_image_count",
            "field_quality"
        ]
    ]
    .head(20)
    .to_string(index=False)
)

# ------------------------------------------------------------
# RECTIFIED IMAGE DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("RECTIFIED IMAGES BY FIELD")
print("=" * 75)

rectified_fields = (
    gps_df[
        gps_df["gps_correction_status"]
        .astype(str)
        .str.upper()
        ==
        "RECTIFIED_HIGH_CONFIDENCE"
    ]
    .groupby("field_id")
    .size()
    .sort_values(ascending=False)
)

print(rectified_fields)

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("FILES SAVED")
print("=" * 75)

print("Image-level mapping:")
print(OUTPUT_CSV)

print("\nField summary:")
print(SUMMARY_CSV)

print("\nOriginal GPS file was NOT modified.")

print("=" * 75)