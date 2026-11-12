# ============================================================
# STEP 5B.7 — ORIGINAL vs RECTIFIED GPS CLUSTER COMPARISON
# ============================================================

import pandas as pd
import numpy as np
import os
from sklearn.cluster import DBSCAN

print("=" * 75)
print("STEP 5B.7 — GPS CLUSTER COMPARISON")
print("=" * 75)

STEP5 = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

ORIGINAL = os.path.join(
    STEP5,
    "image_gps_coordinates.csv"
)

RECTIFIED = os.path.join(
    STEP5,
    "image_gps_coordinates_RECTIFIED.csv"
)

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

original = pd.read_csv(ORIGINAL)
rectified = pd.read_csv(RECTIFIED)

# ------------------------------------------------------------
# GPS ONLY
# ------------------------------------------------------------

def prepare(df):

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

    return df


original = prepare(original)
rectified = prepare(rectified)

print("\nOriginal GPS:", len(original))
print("Rectified GPS:", len(rectified))

# ------------------------------------------------------------
# DBSCAN FUNCTION
# ------------------------------------------------------------

def run_dbscan(df):

    coords = np.radians(
        df[
            ["latitude", "longitude"]
        ].values
    )

    EPS_METERS = 100

    earth_radius = 6371000

    eps_radians = EPS_METERS / earth_radius

    model = DBSCAN(
        eps=eps_radians,
        min_samples=2,
        metric="haversine"
    )

    labels = model.fit_predict(coords)

    df = df.copy()

    df["cluster"] = labels

    valid_clusters = labels[labels >= 0]

    cluster_count = len(
        np.unique(valid_clusters)
    )

    noise_count = np.sum(
        labels == -1
    )

    return df, cluster_count, noise_count


# ------------------------------------------------------------
# RUN ORIGINAL
# ------------------------------------------------------------

orig_clustered, orig_clusters, orig_noise = run_dbscan(
    original
)

# ------------------------------------------------------------
# RUN RECTIFIED
# ------------------------------------------------------------

rect_clustered, rect_clusters, rect_noise = run_dbscan(
    rectified
)

# ------------------------------------------------------------
# COMPARISON
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("CLUSTER COMPARISON")
print("=" * 75)

print(
    f"{'Metric':35} {'Original':15} {'Rectified':15}"
)

print("-" * 75)

print(
    f"{'GPS records':35} "
    f"{len(original):<15} "
    f"{len(rectified):<15}"
)

print(
    f"{'Clusters':35} "
    f"{orig_clusters:<15} "
    f"{rect_clusters:<15}"
)

print(
    f"{'Noise records':35} "
    f"{orig_noise:<15} "
    f"{rect_noise:<15}"
)

print(
    f"{'Noise percentage':35} "
    f"{orig_noise/len(original)*100:.2f}%{'':<8} "
    f"{rect_noise/len(rectified)*100:.2f}%"
)

# ------------------------------------------------------------
# CLUSTER SIZE DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("ORIGINAL LARGEST CLUSTERS")
print("=" * 75)

print(
    orig_clustered[
        orig_clustered["cluster"] >= 0
    ]
    .groupby("cluster")
    .size()
    .sort_values(
        ascending=False
    )
    .head(15)
)

print("\n" + "=" * 75)
print("RECTIFIED LARGEST CLUSTERS")
print("=" * 75)

print(
    rect_clustered[
        rect_clustered["cluster"] >= 0
    ]
    .groupby("cluster")
    .size()
    .sort_values(
        ascending=False
    )
    .head(15)
)

# ------------------------------------------------------------
# SAVE COMPARISON
# ------------------------------------------------------------

comparison = pd.DataFrame({

    "metric": [
        "GPS records",
        "clusters",
        "noise records",
        "noise percentage"
    ],

    "original": [
        len(original),
        orig_clusters,
        orig_noise,
        round(orig_noise / len(original) * 100, 2)
    ],

    "rectified": [
        len(rectified),
        rect_clusters,
        rect_noise,
        round(rect_noise / len(rectified) * 100, 2)
    ]
})

comparison_file = os.path.join(
    STEP5,
    "gps_original_vs_rectified_comparison.csv"
)

comparison.to_csv(
    comparison_file,
    index=False
)

print("\nComparison saved:")
print(comparison_file)

print("\nOriginal GPS file was NOT modified.")
print("=" * 75)