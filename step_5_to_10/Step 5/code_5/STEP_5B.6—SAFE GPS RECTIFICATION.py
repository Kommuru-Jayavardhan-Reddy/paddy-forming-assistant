# ============================================================
# STEP_5B.6—SAFE GPS RECTIFICATION
# ============================================================

import pandas as pd
import numpy as np
import os

print("=" * 75)
print("STEP 5B.6 — SAFE GPS RECTIFICATION")
print("=" * 75)

STEP5 = "/content/drive/MyDrive/final year project/Real_world_test/Step 5"

GPS_FILE = os.path.join(
    STEP5,
    "image_gps_coordinates.csv"
)

CANDIDATE_FILE = os.path.join(
    STEP5,
    "gps_ocr_correction_candidates.csv"
)

OUTPUT_FILE = os.path.join(
    STEP5,
    "image_gps_coordinates_RECTIFIED.csv"
)

REPORT_FILE = os.path.join(
    STEP5,
    "gps_rectification_report.csv"
)

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

gps = pd.read_csv(GPS_FILE)
cand = pd.read_csv(CANDIDATE_FILE)

print("\nOriginal GPS records:", len(gps))
print("Correction candidates:", len(cand))

# ------------------------------------------------------------
# SAFE CANDIDATES
# ------------------------------------------------------------

# Only HIGH confidence
safe = cand[
    cand["confidence"] == "HIGH"
].copy()

# Strong pattern threshold
safe = safe[
    safe["pattern_score"] >= 0.95
].copy()

# ------------------------------------------------------------
# EXTRA SAFETY:
# candidate must be inside established project region
# ------------------------------------------------------------

safe = safe[
    (safe["candidate_latitude"] >= 12.0) &
    (safe["candidate_latitude"] <= 15.0) &
    (safe["candidate_longitude"] >= 78.0) &
    (safe["candidate_longitude"] <= 81.0)
].copy()

print("\nSAFE candidates:", len(safe))

# ------------------------------------------------------------
# REMOVE AMBIGUOUS DUPLICATE IMAGE NAMES
# ------------------------------------------------------------

safe = safe.drop_duplicates(
    subset=["image_name"],
    keep="first"
)

print(
    "Unique images selected for correction:",
    len(safe)
)

# ------------------------------------------------------------
# CREATE LOOKUP
# ------------------------------------------------------------

correction_lookup = safe.set_index(
    "image_name"
)[
    [
        "candidate_latitude",
        "candidate_longitude",
        "pattern_score"
    ]
].to_dict("index")

# ------------------------------------------------------------
# APPLY CORRECTION
# ------------------------------------------------------------

rectified = gps.copy()

rectified["original_latitude"] = rectified["latitude"]
rectified["original_longitude"] = rectified["longitude"]

rectified["gps_correction_status"] = "UNCHANGED"
rectified["gps_correction_score"] = np.nan

for idx, row in rectified.iterrows():

    image_name = row["image_name"]

    if image_name in correction_lookup:

        correction = correction_lookup[image_name]

        rectified.at[
            idx, "latitude"
        ] = correction["candidate_latitude"]

        rectified.at[
            idx, "longitude"
        ] = correction["candidate_longitude"]

        rectified.at[
            idx, "gps_correction_status"
        ] = "RECTIFIED_HIGH_CONFIDENCE"

        rectified.at[
            idx, "gps_correction_score"
        ] = correction["pattern_score"]

# ------------------------------------------------------------
# SAVE RECTIFIED FILE
# ------------------------------------------------------------

rectified.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# CREATE REPORT
# ------------------------------------------------------------

report = rectified[
    rectified["gps_correction_status"]
    == "RECTIFIED_HIGH_CONFIDENCE"
].copy()

report = report[
    [
        "image_name",
        "image_path",
        "original_latitude",
        "original_longitude",
        "latitude",
        "longitude",
        "gps_correction_score",
        "gps_correction_status"
    ]
]

report.to_csv(
    REPORT_FILE,
    index=False
)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("RECTIFICATION SUMMARY")
print("=" * 75)

print(
    "Original records:",
    len(gps)
)

print(
    "Rectified records:",
    len(report)
)

print(
    "Unchanged records:",
    len(rectified) - len(report)
)

print("\nCorrection status:")
print(
    rectified["gps_correction_status"]
    .value_counts()
)

# ------------------------------------------------------------
# SHOW CORRECTIONS
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("APPLIED CORRECTIONS")
print("=" * 75)

if len(report) > 0:

    print(
        report[
            [
                "image_name",
                "original_latitude",
                "original_longitude",
                "latitude",
                "longitude",
                "gps_correction_score"
            ]
        ]
        .head(100)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("FILES SAVED")
print("=" * 75)

print("RECTIFIED GPS:")
print(OUTPUT_FILE)

print("\nRECTIFICATION REPORT:")
print(REPORT_FILE)

print("\nOriginal image_gps_coordinates.csv was NOT modified.")

print("=" * 75)