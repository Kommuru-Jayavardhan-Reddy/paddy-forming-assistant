# ============================================================
# STEP 5B.9 — SUSPICIOUS GPS SUMMARY
# ============================================================

from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

SATELLITE_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/Step 5"
)

RESULTS_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/Step 5"
)

IMAGE_GPS_CSV = (
    SATELLITE_FOLDER / "image_gps_coordinates.csv"
)

OUTPUT_CSV = (
    SATELLITE_FOLDER /
    "suspicious_gps_summary.csv"
)

REPORT_FILE = (
    RESULTS_FOLDER /
    "Step_5B_Suspicious_GPS_Summary.txt"
)

# ------------------------------------------------------------
# LOAD ORIGINAL GPS DATA
# ------------------------------------------------------------

df = pd.read_csv(IMAGE_GPS_CSV)

# ------------------------------------------------------------
# Identify suspicious coordinates
# ------------------------------------------------------------

valid_region = (
    df["latitude"].between(12.5, 14.0)
    &
    df["longitude"].between(78.5, 80.5)
)

suspicious = df[
    (df["status"] == "GPS_FOUND")
    & (~valid_region)
].copy()

# ------------------------------------------------------------
# Extract disease class from image_path
# ------------------------------------------------------------

def get_disease_class(path):

    parts = Path(str(path)).parts

    # Find folder immediately after "gps"
    for i, part in enumerate(parts):

        if part.lower() == "gps" and i + 1 < len(parts):
            return parts[i + 1]

    return "UNKNOWN"


suspicious["disease_class"] = (
    suspicious["image_path"]
    .apply(get_disease_class)
)

# ------------------------------------------------------------
# Rename columns clearly
# ------------------------------------------------------------

summary = suspicious[
    [
        "image_name",
        "image_path",
        "latitude",
        "longitude",
        "status",
        "disease_class"
    ]
].copy()

summary = summary.rename(
    columns={
        "latitude": "actual_ocr_latitude",
        "longitude": "actual_ocr_longitude"
    }
)

# ------------------------------------------------------------
# Sort
# ------------------------------------------------------------

summary = summary.sort_values(
    [
        "actual_ocr_latitude",
        "actual_ocr_longitude",
        "disease_class"
    ]
).reset_index(drop=True)

# ------------------------------------------------------------
# SAVE CSV
# ------------------------------------------------------------

summary.to_csv(
    OUTPUT_CSV,
    index=False
)

# ------------------------------------------------------------
# CREATE COORDINATE GROUP SUMMARY
# ------------------------------------------------------------

coordinate_groups = (
    summary
    .groupby(
        [
            "actual_ocr_latitude",
            "actual_ocr_longitude"
        ]
    )
    .agg(
        image_count=("image_name", "count"),
        disease_classes=(
            "disease_class",
            lambda x: ", ".join(
                sorted(x.unique())
            )
        )
    )
    .reset_index()
    .sort_values(
        "image_count",
        ascending=False
    )
)

# ------------------------------------------------------------
# SAVE REPORT
# ------------------------------------------------------------

RESULTS_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "STEP 5B — SUSPICIOUS GPS SUMMARY\n"
    )

    f.write("=" * 70 + "\n\n")

    f.write(
        f"Total GPS records: {len(df)}\n"
    )

    f.write(
        f"Suspicious records: {len(summary)}\n"
    )

    f.write(
        f"Unique suspicious coordinates: "
        f"{len(coordinate_groups)}\n\n"
    )

    f.write(
        "COORDINATE GROUPS\n"
    )

    f.write("=" * 70 + "\n")

    f.write(
        coordinate_groups.to_string(
            index=False
        )
    )

    f.write("\n\n")

    f.write(
        "IMPORTANT:\n"
    )

    f.write(
        "These coordinates are reported by OCR from "
        "the GPS overlay in the images.\n"
    )

    f.write(
        "No coordinates were manually corrected.\n"
    )

# ------------------------------------------------------------
# DISPLAY RESULTS
# ------------------------------------------------------------

print("=" * 70)
print("STEP 5B — SUSPICIOUS GPS SUMMARY")
print("=" * 70)

print(
    "\nTotal GPS records:",
    len(df)
)

print(
    "Suspicious records:",
    len(summary)
)

print(
    "Unique suspicious coordinates:",
    len(coordinate_groups)
)

print("\n" + "=" * 70)
print("COORDINATE GROUPS")
print("=" * 70)

display(coordinate_groups)

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print("\nCSV:")
print(OUTPUT_CSV)

print("\nReport:")
print(REPORT_FILE)

print("\n✅ No original GPS files were modified.")