# ============================================================================
# STEP 5C.3 — SAFE GPS FIELD → TRUSTED SATELLITE FIELD MAPPING
# ============================================================================
# IMPORTANT:
# - Uses ORIGINAL GPS file only
# - Does NOT use previous RECTIFIED GPS file
# - Does NOT modify original GPS coordinates
# - Does NOT modify Step 6 embeddings
# - Creates a new validation/mapping file only
# ============================================================================

import pandas as pd
import numpy as np
import os
from math import radians, sin, cos, sqrt, atan2
from sklearn.cluster import DBSCAN

# ============================================================================
# PATHS
# ============================================================================

STEP5_DIR = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

GPS_FILE = os.path.join(
    STEP5_DIR,
    "image_gps_coordinates.csv"
)

SAT_FIELD_FILE = os.path.join(
    STEP5_DIR,
    "clean_field_candidates_renamed.csv"
)

OUTPUT_FIELD_FILE = os.path.join(
    STEP5_DIR,
    "step5C3_gps_field_to_satellite_mapping.csv"
)

OUTPUT_IMAGE_FILE = os.path.join(
    STEP5_DIR,
    "step5C3_image_to_satellite_mapping_candidates.csv"
)

SUMMARY_FILE = os.path.join(
    STEP5_DIR,
    "step5C3_mapping_summary.txt"
)

# ============================================================================
# SETTINGS
# ============================================================================

# DBSCAN field grouping
FIELD_RADIUS_METERS = 100
MIN_SAMPLES = 2

# Mapping decision thresholds
CONFIRMED_KM = 1.0
REVIEW_KM = 5.0

# Project region
LAT_MIN = 12.0
LAT_MAX = 15.0
LON_MIN = 78.0
LON_MAX = 81.0

# ============================================================================
# HAVERSINE
# ============================================================================

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
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    return 2 * R * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

# ============================================================================
# HEADER
# ============================================================================

print("=" * 80)
print("STEP 5C.3 — SAFE GPS FIELD → TRUSTED SATELLITE FIELD MAPPING")
print("=" * 80)

# ============================================================================
# LOAD ORIGINAL GPS
# ============================================================================

gps = pd.read_csv(GPS_FILE)

print("\nOriginal GPS file:")
print(GPS_FILE)

print(f"Total records: {len(gps)}")

# ============================================================================
# CHECK GPS COLUMNS
# ============================================================================

required_gps = [
    "latitude",
    "longitude"
]

for col in required_gps:

    if col not in gps.columns:

        raise ValueError(
            f"Missing GPS column: {col}\n"
            f"Available columns: {list(gps.columns)}"
        )

# ============================================================================
# NUMERIC CONVERSION
# ============================================================================

gps["latitude"] = pd.to_numeric(
    gps["latitude"],
    errors="coerce"
)

gps["longitude"] = pd.to_numeric(
    gps["longitude"],
    errors="coerce"
)

gps_valid = gps[
    gps["latitude"].notna() &
    gps["longitude"].notna()
].copy()

print(f"Records with GPS: {len(gps_valid)}")

# ============================================================================
# PROJECT REGION FILTER
# ============================================================================

gps_valid["inside_project_region"] = (
    (gps_valid["latitude"] >= LAT_MIN) &
    (gps_valid["latitude"] <= LAT_MAX) &
    (gps_valid["longitude"] >= LON_MIN) &
    (gps_valid["longitude"] <= LON_MAX)
)

gps_region = gps_valid[
    gps_valid["inside_project_region"]
].copy()

gps_outside = gps_valid[
    ~gps_valid["inside_project_region"]
].copy()

print(f"Inside project region: {len(gps_region)}")
print(f"Outside project region: {len(gps_outside)}")

# ============================================================================
# DBSCAN FIELD CLUSTERING
# ============================================================================

print("\n" + "=" * 80)
print("GPS FIELD CLUSTERING")
print("=" * 80)

coords_rad = np.radians(
    gps_region[
        ["latitude", "longitude"]
    ].values
)

EARTH_RADIUS_M = 6371000.0

eps_radians = (
    FIELD_RADIUS_METERS /
    EARTH_RADIUS_M
)

dbscan = DBSCAN(
    eps=eps_radians,
    min_samples=MIN_SAMPLES,
    metric="haversine"
)

gps_region["cluster"] = dbscan.fit_predict(
    coords_rad
)

# Remove DBSCAN noise
clustered = gps_region[
    gps_region["cluster"] != -1
].copy()

noise = gps_region[
    gps_region["cluster"] == -1
].copy()

print(f"GPS records clustered: {len(clustered)}")
print(f"GPS noise records: {len(noise)}")

# ============================================================================
# CREATE GPS FIELD CENTERS
# ============================================================================

field_rows = []

unique_clusters = sorted(
    clustered["cluster"].unique()
)

for new_id, cluster_id in enumerate(
    unique_clusters,
    start=1
):

    field_data = clustered[
        clustered["cluster"] == cluster_id
    ]

    center_lat = field_data["latitude"].mean()
    center_lon = field_data["longitude"].mean()

    field_id = f"GPS_FIELD_{new_id:03d}"

    field_rows.append({

        "gps_field_id": field_id,

        "cluster_id": int(cluster_id),

        "gps_image_count": len(field_data),

        "gps_latitude": center_lat,

        "gps_longitude": center_lon

    })

gps_fields = pd.DataFrame(field_rows)

print(f"GPS fields created: {len(gps_fields)}")

# ============================================================================
# LOAD TRUSTED SATELLITE FIELDS
# ============================================================================

sat = pd.read_csv(
    SAT_FIELD_FILE
)

print("\n" + "=" * 80)
print("TRUSTED SATELLITE FIELDS")
print("=" * 80)

print(f"Trusted satellite fields: {len(sat)}")

# ============================================================================
# DETECT SATELLITE LAT/LON COLUMNS
# ============================================================================

possible_lat = [
    "latitude",
    "lat",
    "field_latitude"
]

possible_lon = [
    "longitude",
    "lon",
    "field_longitude"
]

sat_lat_col = None
sat_lon_col = None

for col in possible_lat:

    if col in sat.columns:

        sat_lat_col = col
        break

for col in possible_lon:

    if col in sat.columns:

        sat_lon_col = col
        break

if sat_lat_col is None or sat_lon_col is None:

    raise ValueError(
        "Could not identify latitude/longitude columns "
        f"in satellite field file.\nColumns: {list(sat.columns)}"
    )

# ============================================================================
# DETECT SATELLITE FIELD ID
# ============================================================================

possible_field_id = [
    "field_id",
    "clean_field_id",
    "satellite_field_id"
]

sat_field_col = None

for col in possible_field_id:

    if col in sat.columns:

        sat_field_col = col
        break

if sat_field_col is None:

    raise ValueError(
        "Could not identify satellite field ID column.\n"
        f"Columns: {list(sat.columns)}"
    )

# ============================================================================
# CLEAN SATELLITE DATA
# ============================================================================

sat[sat_lat_col] = pd.to_numeric(
    sat[sat_lat_col],
    errors="coerce"
)

sat[sat_lon_col] = pd.to_numeric(
    sat[sat_lon_col],
    errors="coerce"
)

sat = sat[
    sat[sat_lat_col].notna() &
    sat[sat_lon_col].notna()
].copy()

print(
    f"Usable trusted satellite fields: {len(sat)}"
)

# ============================================================================
# MAP EACH GPS FIELD TO NEAREST TRUSTED SATELLITE FIELD
# ============================================================================

mapping_rows = []

for _, gps_field in gps_fields.iterrows():

    gps_lat = gps_field["gps_latitude"]
    gps_lon = gps_field["gps_longitude"]

    best_distance = float("inf")
    best_sat_field = None
    best_sat_lat = np.nan
    best_sat_lon = np.nan

    # --------------------------------------------------------------
    # Find nearest trusted satellite field
    # --------------------------------------------------------------

    for _, sat_field in sat.iterrows():

        sat_lat = sat_field[sat_lat_col]
        sat_lon = sat_field[sat_lon_col]

        distance = haversine_km(
            gps_lat,
            gps_lon,
            sat_lat,
            sat_lon
        )

        if distance < best_distance:

            best_distance = distance

            best_sat_field = sat_field[
                sat_field_col
            ]

            best_sat_lat = sat_lat
            best_sat_lon = sat_lon

    # --------------------------------------------------------------
    # Decision
    # --------------------------------------------------------------

    if best_distance <= CONFIRMED_KM:

        decision = "CONFIRMED"

    elif best_distance <= REVIEW_KM:

        decision = "REVIEW"

    else:

        decision = "REJECT"

    mapping_rows.append({

        "gps_field_id":
            gps_field["gps_field_id"],

        "gps_image_count":
            gps_field["gps_image_count"],

        "gps_latitude":
            gps_lat,

        "gps_longitude":
            gps_lon,

        "nearest_satellite_field":
            best_sat_field,

        "satellite_latitude":
            best_sat_lat,

        "satellite_longitude":
            best_sat_lon,

        "distance_km":
            best_distance,

        "decision":
            decision

    })

field_mapping = pd.DataFrame(
    mapping_rows
)

# ============================================================================
# SORT BY DISTANCE
# ============================================================================

field_mapping = field_mapping.sort_values(
    "distance_km"
).reset_index(drop=True)

# ============================================================================
# SAVE FIELD MAPPING
# ============================================================================

field_mapping.to_csv(
    OUTPUT_FIELD_FILE,
    index=False
)

# ============================================================================
# CREATE IMAGE → SATELLITE CANDIDATE MAPPING
# ============================================================================

# Map cluster → GPS field ID
cluster_to_field = dict(
    zip(
        gps_fields["cluster_id"],
        gps_fields["gps_field_id"]
    )
)

clustered["gps_field_id"] = (
    clustered["cluster"]
    .map(cluster_to_field)
)

# Merge field mapping
image_candidates = clustered.merge(
    field_mapping[
        [
            "gps_field_id",
            "nearest_satellite_field",
            "distance_km",
            "decision"
        ]
    ],
    on="gps_field_id",
    how="left"
)

# ============================================================================
# SAVE IMAGE CANDIDATES
# ============================================================================

image_candidates.to_csv(
    OUTPUT_IMAGE_FILE,
    index=False
)

# ============================================================================
# SUMMARY
# ============================================================================

decision_counts = (
    field_mapping["decision"]
    .value_counts()
)

print("\n" + "=" * 80)
print("FIELD MAPPING SUMMARY")
print("=" * 80)

print(decision_counts)

# ============================================================================
# IMAGE COUNTS BY DECISION
# ============================================================================

image_decision_counts = (
    image_candidates
    .groupby("decision")
    .size()
)

print("\n" + "=" * 80)
print("IMAGE MAPPING SUMMARY")
print("=" * 80)

print(image_decision_counts)

# ============================================================================
# SHOW CONFIRMED
# ============================================================================

confirmed = field_mapping[
    field_mapping["decision"] == "CONFIRMED"
].copy()

print("\n" + "=" * 80)
print("CONFIRMED GPS → SATELLITE FIELDS")
print("=" * 80)

print(
    confirmed[
        [
            "gps_field_id",
            "gps_image_count",
            "nearest_satellite_field",
            "distance_km",
            "decision"
        ]
    ].to_string(index=False)
)

# ============================================================================
# SHOW REVIEW
# ============================================================================

review = field_mapping[
    field_mapping["decision"] == "REVIEW"
].copy()

print("\n" + "=" * 80)
print("REVIEW FIELDS")
print("=" * 80)

if len(review) == 0:

    print("No REVIEW fields.")

else:

    print(
        review[
            [
                "gps_field_id",
                "gps_image_count",
                "nearest_satellite_field",
                "distance_km",
                "decision"
            ]
        ].to_string(index=False)
    )

# ============================================================================
# SHOW REJECTED
# ============================================================================

rejected = field_mapping[
    field_mapping["decision"] == "REJECT"
].copy()

print("\n" + "=" * 80)
print("REJECTED FIELDS")
print("=" * 80)

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
    ].to_string(index=False)
)

# ============================================================================
# SAVE SUMMARY TEXT
# ============================================================================

with open(
    SUMMARY_FILE,
    "w"
) as f:

    f.write(
        "STEP 5C.3 — SAFE GPS FIELD TO SATELLITE FIELD MAPPING\n"
    )

    f.write("=" * 70 + "\n\n")

    f.write(
        f"Original GPS records: {len(gps)}\n"
    )

    f.write(
        f"GPS records with coordinates: {len(gps_valid)}\n"
    )

    f.write(
        f"GPS records inside project region: {len(gps_region)}\n"
    )

    f.write(
        f"GPS records outside project region: {len(gps_outside)}\n"
    )

    f.write(
        f"GPS fields created: {len(gps_fields)}\n"
    )

    f.write(
        f"Trusted satellite fields: {len(sat)}\n\n"
    )

    for decision, count in decision_counts.items():

        f.write(
            f"{decision}: {count} fields\n"
        )

    f.write("\n")

    f.write(
        f"Confirmed threshold: <= {CONFIRMED_KM} km\n"
    )

    f.write(
        f"Review threshold: > {CONFIRMED_KM} km and <= {REVIEW_KM} km\n"
    )

    f.write(
        f"Reject threshold: > {REVIEW_KM} km\n"
    )

# ============================================================================
# FINAL MESSAGE
# ============================================================================

print("\n" + "=" * 80)
print("OUTPUT FILES")
print("=" * 80)

print(
    f"\nField mapping:\n{OUTPUT_FIELD_FILE}"
)

print(
    f"\nImage candidates:\n{OUTPUT_IMAGE_FILE}"
)

print(
    f"\nSummary:\n{SUMMARY_FILE}"
)

print("\n" + "=" * 80)
print("IMPORTANT")
print("=" * 80)

print("""
1. Original GPS file was NOT modified.
2. No GPS coordinate correction was applied.
3. Step 6 satellite embeddings were NOT changed.
4. Step 7 should NOT be run yet.
5. Only CONFIRMED fields should eventually be considered for
   image → satellite embedding mapping.
""")

print("=" * 80)