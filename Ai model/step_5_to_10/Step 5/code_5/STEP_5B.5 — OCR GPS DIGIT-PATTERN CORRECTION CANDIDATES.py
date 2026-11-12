# ============================================================
# STEP 5B.5 — OCR GPS DIGIT-PATTERN CORRECTION CANDIDATES
# ============================================================

import pandas as pd
import numpy as np
import os

print("=" * 75)
print("STEP 5B.5 — OCR GPS DIGIT-PATTERN ANALYSIS")
print("=" * 75)

STEP5_FOLDER = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

GPS_FILE = os.path.join(
    STEP5_FOLDER,
    "image_gps_coordinates.csv"
)

OUTPUT_FILE = os.path.join(
    STEP5_FOLDER,
    "gps_ocr_correction_candidates.csv"
)

# ------------------------------------------------------------
# LOAD GPS
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

print("\nTotal GPS records:", len(df))

# ------------------------------------------------------------
# PROJECT REGION
# ------------------------------------------------------------

LAT_MIN = 12.0
LAT_MAX = 15.0

LON_MIN = 78.0
LON_MAX = 81.0

valid = df[
    (df["latitude"] >= LAT_MIN) &
    (df["latitude"] <= LAT_MAX) &
    (df["longitude"] >= LON_MIN) &
    (df["longitude"] <= LON_MAX)
].copy()

suspicious = df[
    ~(
        (df["latitude"] >= LAT_MIN) &
        (df["latitude"] <= LAT_MAX) &
        (df["longitude"] >= LON_MIN) &
        (df["longitude"] <= LON_MAX)
    )
].copy()

print("Valid project-region GPS:", len(valid))
print("Suspicious GPS:", len(suspicious))

# ------------------------------------------------------------
# COORDINATE STRING
# ------------------------------------------------------------

def coord_string(value):
    return f"{float(value):.6f}"


def fractional_part(value):
    s = coord_string(value)
    return s.split(".")[1]


# ------------------------------------------------------------
# DIGIT SIMILARITY
# ------------------------------------------------------------

def digit_similarity(a, b):

    a = coord_string(a).replace(".", "")
    b = coord_string(b).replace(".", "")

    matches = sum(
        x == y for x, y in zip(a, b)
    )

    return matches / max(len(a), len(b))


def fractional_similarity(a, b):

    a = fractional_part(a)
    b = fractional_part(b)

    matches = sum(
        x == y for x, y in zip(a, b)
    )

    return matches / 6.0


# ------------------------------------------------------------
# UNIQUE VALID COORDINATES
# ------------------------------------------------------------

valid_coords = (
    valid[
        ["latitude", "longitude"]
    ]
    .drop_duplicates()
    .reset_index(drop=True)
)

print(
    "Unique valid coordinates:",
    len(valid_coords)
)

# ------------------------------------------------------------
# FIND BEST CANDIDATE
# ------------------------------------------------------------

results = []

for _, row in suspicious.iterrows():

    old_lat = float(row["latitude"])
    old_lon = float(row["longitude"])

    best_score = -1
    best_lat = np.nan
    best_lon = np.nan

    best_lat_similarity = 0
    best_lon_similarity = 0

    # --------------------------------------------
    # Compare with every trusted project GPS
    # --------------------------------------------

    for _, ref in valid_coords.iterrows():

        ref_lat = float(ref["latitude"])
        ref_lon = float(ref["longitude"])

        lat_sim = fractional_similarity(
            old_lat,
            ref_lat
        )

        lon_sim = fractional_similarity(
            old_lon,
            ref_lon
        )

        full_lat_sim = digit_similarity(
            old_lat,
            ref_lat
        )

        full_lon_sim = digit_similarity(
            old_lon,
            ref_lon
        )

        # Fractional digits are given higher weight
        score = (
            0.40 * lat_sim +
            0.40 * lon_sim +
            0.10 * full_lat_sim +
            0.10 * full_lon_sim
        )

        if score > best_score:

            best_score = score

            best_lat = ref_lat
            best_lon = ref_lon

            best_lat_similarity = lat_sim
            best_lon_similarity = lon_sim

    # --------------------------------------------
    # Confidence
    # --------------------------------------------

    if best_score >= 0.90:
        confidence = "HIGH"

    elif best_score >= 0.80:
        confidence = "MEDIUM"

    elif best_score >= 0.70:
        confidence = "LOW"

    else:
        confidence = "UNSAFE"

    results.append({

        "image_name":
            row.get("image_name", ""),

        "image_path":
            row.get("image_path", ""),

        "original_latitude":
            old_lat,

        "original_longitude":
            old_lon,

        "candidate_latitude":
            best_lat,

        "candidate_longitude":
            best_lon,

        "latitude_fraction_similarity":
            round(best_lat_similarity, 3),

        "longitude_fraction_similarity":
            round(best_lon_similarity, 3),

        "pattern_score":
            round(best_score, 3),

        "confidence":
            confidence
    })


result = pd.DataFrame(results)

# ------------------------------------------------------------
# SORT
# ------------------------------------------------------------

result = result.sort_values(
    ["confidence", "pattern_score"],
    ascending=[True, False]
)

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
print("CORRECTION CANDIDATE SUMMARY")
print("=" * 75)

print(
    result["confidence"]
    .value_counts()
)

# ------------------------------------------------------------
# SHOW HIGH CONFIDENCE
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("HIGH CONFIDENCE CANDIDATES")
print("=" * 75)

high = result[
    result["confidence"] == "HIGH"
]

print(
    "High-confidence records:",
    len(high)
)

if len(high) > 0:

    print(
        high[
            [
                "image_name",
                "original_latitude",
                "original_longitude",
                "candidate_latitude",
                "candidate_longitude",
                "latitude_fraction_similarity",
                "longitude_fraction_similarity",
                "pattern_score",
                "confidence"
            ]
        ]
        .head(100)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# SHOW MEDIUM
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("MEDIUM CONFIDENCE CANDIDATES")
print("=" * 75)

medium = result[
    result["confidence"] == "MEDIUM"
]

print(
    "Medium-confidence records:",
    len(medium)
)

if len(medium) > 0:

    print(
        medium[
            [
                "original_latitude",
                "original_longitude",
                "candidate_latitude",
                "candidate_longitude",
                "pattern_score",
                "confidence"
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
print("Original image_gps_coordinates.csv was NOT modified.")
print("No coordinate was automatically corrected.")
print("These are ONLY correction candidates.")

print("=" * 75)