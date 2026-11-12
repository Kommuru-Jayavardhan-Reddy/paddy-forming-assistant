# ============================================================
# STEP 5B — GPS SPATIAL CLUSTERING
# DBSCAN + 100 metre radius
# ============================================================

from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN

# ============================================================
# 1. PATHS
# ============================================================

STEP5_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/Step 5"
)

INPUT_CSV = STEP5_FOLDER / "image_gps_coordinates.csv"

OUTPUT_CSV = STEP5_FOLDER / "gps_spatial_clusters.csv"

SUMMARY_CSV = STEP5_FOLDER / "gps_cluster_summary.csv"


# ============================================================
# 2. CHECK INPUT FILE
# ============================================================

print("=" * 80)
print("STEP 5B — GPS SPATIAL CLUSTERING")
print("=" * 80)

print("\nInput file:")
print(INPUT_CSV)

if not INPUT_CSV.exists():
    raise FileNotFoundError(
        f"\n❌ INPUT FILE NOT FOUND:\n{INPUT_CSV}"
    )

print("\n✅ Input file found")


# ============================================================
# 3. LOAD GPS DATA
# ============================================================

df = pd.read_csv(INPUT_CSV)

print("\nTotal records in CSV:", len(df))

gps = df[
    df["status"] == "GPS_FOUND"
].copy()

gps = gps.dropna(
    subset=["latitude", "longitude"]
).reset_index(drop=True)

print("Valid GPS records:", len(gps))


# ============================================================
# 4. PREPARE COORDINATES
# ============================================================

coordinates = gps[
    ["latitude", "longitude"]
].to_numpy()

coordinates_rad = np.radians(coordinates)


# ============================================================
# 5. DBSCAN SETTINGS
# ============================================================

EARTH_RADIUS_METERS = 6371000

# Current clustering radius
EPS_METERS = 100

eps_radians = (
    EPS_METERS /
    EARTH_RADIUS_METERS
)

print("\nDBSCAN settings:")
print("Radius:", EPS_METERS, "metres")
print("Minimum samples:", 2)


# ============================================================
# 6. RUN DBSCAN
# ============================================================

cluster_model = DBSCAN(
    eps=eps_radians,
    min_samples=2,
    metric="haversine"
)

cluster_labels = cluster_model.fit_predict(
    coordinates_rad
)

gps["cluster_id"] = cluster_labels


# ============================================================
# 7. CLUSTER INFORMATION
# ============================================================

cluster_ids = sorted(
    [
        x
        for x in gps["cluster_id"].unique()
        if x != -1
    ]
)

noise_count = (
    gps["cluster_id"] == -1
).sum()

print("\n" + "=" * 80)
print("CLUSTER RESULT")
print("=" * 80)

print("\nClusters found:", len(cluster_ids))
print("Noise GPS records:", noise_count)


# ============================================================
# 8. CREATE FIELD IDs
# ============================================================

cluster_to_field = {}

for i, cluster_id in enumerate(
    cluster_ids,
    start=1
):

    cluster_to_field[
        cluster_id
    ] = f"FIELD_{i:02d}"


gps["field_id"] = (
    gps["cluster_id"]
    .map(cluster_to_field)
)

gps.loc[
    gps["cluster_id"] == -1,
    "field_id"
] = "NOISE"


# ============================================================
# 9. CREATE CLUSTER SUMMARY
# ============================================================

summary_rows = []

for cluster_id in cluster_ids:

    cluster_data = gps[
        gps["cluster_id"] == cluster_id
    ]

    center_lat = cluster_data[
        "latitude"
    ].mean()

    center_lon = cluster_data[
        "longitude"
    ].mean()

    summary_rows.append({

        "field_id":
            cluster_to_field[cluster_id],

        "cluster_id":
            cluster_id,

        "image_count":
            len(cluster_data),

        "center_latitude":
            round(center_lat, 6),

        "center_longitude":
            round(center_lon, 6),

        "min_latitude":
            round(
                cluster_data["latitude"].min(),
                6
            ),

        "max_latitude":
            round(
                cluster_data["latitude"].max(),
                6
            ),

        "min_longitude":
            round(
                cluster_data["longitude"].min(),
                6
            ),

        "max_longitude":
            round(
                cluster_data["longitude"].max(),
                6
            )
    })


summary = pd.DataFrame(
    summary_rows
)


# ============================================================
# 10. SORT BY IMAGE COUNT
# ============================================================

summary = summary.sort_values(
    "image_count",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 11. SAVE IMAGE-LEVEL CLUSTERS
# ============================================================

gps.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# 12. SAVE CLUSTER SUMMARY
# ============================================================

summary.to_csv(
    SUMMARY_CSV,
    index=False
)


# ============================================================
# 13. DISPLAY SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("FIELD CLUSTER SUMMARY")
print("=" * 80)

display(summary)


# ============================================================
# 14. IMAGE COUNT DISTRIBUTION
# ============================================================

print("\n" + "=" * 80)
print("FIELD IMAGE COUNT")
print("=" * 80)

display(
    summary[
        [
            "field_id",
            "image_count",
            "center_latitude",
            "center_longitude"
        ]
    ]
)


# ============================================================
# 15. NOISE RECORDS
# ============================================================

noise = gps[
    gps["cluster_id"] == -1
]

print("\n" + "=" * 80)
print("NOISE RECORDS")
print("=" * 80)

print("Noise count:", len(noise))

if len(noise) > 0:

    display(
        noise[
            [
                "image_name",
                "latitude",
                "longitude"
            ]
        ].head(30)
    )


# ============================================================
# 16. SAVE INFORMATION
# ============================================================

print("\n" + "=" * 80)
print("FILES SAVED")
print("=" * 80)

print("\nImage-level clusters:")
print(OUTPUT_CSV)

print("\nCluster summary:")
print(SUMMARY_CSV)


# ============================================================
# 17. FINAL CHECK
# ============================================================

print("\n" + "=" * 80)
print("FINAL CHECK")
print("=" * 80)

print("\nOriginal CSV:")
print(INPUT_CSV)

print("\nOriginal image_gps_coordinates.csv was NOT modified.")

print("\nCoordinates were NOT manually changed.")

print("\nDBSCAN radius:", EPS_METERS, "metres")

print("\nTotal GPS records:", len(gps))

print("Total fields:", len(cluster_ids))

print("Noise records:", noise_count)

print("\n" + "=" * 80)
print("✅ STEP 5B GPS SPATIAL CLUSTERING COMPLETE")
print("=" * 80)