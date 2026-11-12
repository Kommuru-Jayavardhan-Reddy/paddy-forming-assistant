# ============================================================
# STEP 5B  — FULL OCR GPS COORDINATE EXTRACTION
# ============================================================

from pathlib import Path
from PIL import Image
import pytesseract
import re
import cv2
import numpy as np
import pandas as pd
from datetime import datetime

# ============================================================
# PATHS
# ============================================================

GPS_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/gps"
)

SATELLITE_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/Step 5"
)

CODE_FOLDER = Path(
    "/content/drive/MyDrive/final year project/code"
)

RESULT_FOLDER = Path(
    "/content/drive/MyDrive/final year project/results"
)

SATELLITE_FOLDER.mkdir(parents=True, exist_ok=True)
CODE_FOLDER.mkdir(parents=True, exist_ok=True)
RESULT_FOLDER.mkdir(parents=True, exist_ok=True)

# Output files
IMAGE_GPS_CSV = SATELLITE_FOLDER / "image_gps_coordinates.csv"
FIELD_CSV = SATELLITE_FOLDER / "field_locations.csv"
REPORT_FILE = RESULT_FOLDER / "Step_5B_OCR_GPS_Extraction.txt"
CODE_FILE = CODE_FOLDER / "Step_5B_OCR_GPS_Extraction.py"

# ============================================================
# FIND ALL IMAGES
# ============================================================

image_files = []

for ext in [
    "*.jpg", "*.jpeg",
    "*.JPG", "*.JPEG",
    "*.png", "*.PNG"
]:
    image_files.extend(GPS_FOLDER.rglob(ext))

image_files = sorted(image_files)

print("=" * 70)
print("STEP 5B — FULL OCR GPS EXTRACTION")
print("=" * 70)

print("\nGPS folder:")
print(GPS_FOLDER)

print("\nTotal images found:", len(image_files))

# ============================================================
# OCR FUNCTION
# ============================================================

def extract_gps_from_image(image_path):

    try:

        # ------------------------------------------------------
        # Open image
        # ------------------------------------------------------

        img = Image.open(image_path).convert("RGB")

        width, height = img.size

        # ------------------------------------------------------
        # GPS overlay is normally at bottom
        # Use bottom 40%
        # ------------------------------------------------------

        crop = img.crop(
            (
                0,
                int(height * 0.60),
                width,
                height
            )
        )

        # ------------------------------------------------------
        # Upscale for OCR
        # ------------------------------------------------------

        crop = crop.resize(
            (
                crop.width * 4,
                crop.height * 4
            )
        )

        # ------------------------------------------------------
        # Convert to OpenCV
        # ------------------------------------------------------

        crop_cv = cv2.cvtColor(
            np.array(crop),
            cv2.COLOR_RGB2BGR
        )

        # ------------------------------------------------------
        # Grayscale
        # ------------------------------------------------------

        gray = cv2.cvtColor(
            crop_cv,
            cv2.COLOR_BGR2GRAY
        )

        # ------------------------------------------------------
        # Improve contrast
        # ------------------------------------------------------

        gray = cv2.convertScaleAbs(
            gray,
            alpha=2.0,
            beta=0
        )

        # ------------------------------------------------------
        # OCR
        # ------------------------------------------------------

        text = pytesseract.image_to_string(
            gray,
            config="--psm 6"
        )

        # ------------------------------------------------------
        # Extract decimal numbers
        # ------------------------------------------------------

        numbers = re.findall(
            r'\d{1,3}\.\d{4,}',
            text
        )

        numbers = [float(x) for x in numbers]

        # ------------------------------------------------------
        # Find valid India coordinate pair
        # ------------------------------------------------------

        for i in range(len(numbers) - 1):

            lat = numbers[i]
            lon = numbers[i + 1]

            # India coordinate sanity check
            if (
                6 <= lat <= 38
                and 68 <= lon <= 98
            ):

                return {
                    "latitude": lat,
                    "longitude": lon,
                    "ocr_text": text,
                    "status": "GPS_FOUND"
                }

        return {
            "latitude": None,
            "longitude": None,
            "ocr_text": text,
            "status": "GPS_NOT_FOUND"
        }

    except Exception as e:

        return {
            "latitude": None,
            "longitude": None,
            "ocr_text": "",
            "status": f"ERROR: {str(e)}"
        }


# ============================================================
# PROCESS ALL IMAGES
# ============================================================

records = []

for i, image_path in enumerate(image_files, 1):

    result = extract_gps_from_image(image_path)

    records.append({
        "image_name": image_path.name,
        "image_path": str(image_path),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "status": result["status"]
    })

    # Progress
    if i % 25 == 0 or i == len(image_files):

        gps_count = sum(
            r["status"] == "GPS_FOUND"
            for r in records
        )

        print(
            f"Processed {i}/{len(image_files)} "
            f"| GPS found: {gps_count}"
        )


# ============================================================
# IMAGE → GPS DATAFRAME
# ============================================================

image_gps_df = pd.DataFrame(records)

# Save complete image-to-coordinate mapping
image_gps_df.to_csv(
    IMAGE_GPS_CSV,
    index=False
)

print("\n" + "=" * 70)
print("IMAGE GPS EXTRACTION RESULT")
print("=" * 70)

total = len(image_gps_df)

gps_found = (
    image_gps_df["status"] == "GPS_FOUND"
).sum()

gps_failed = total - gps_found

print("\nImages scanned :", total)
print("GPS found      :", gps_found)
print("GPS not found  :", gps_failed)

# ============================================================
# CREATE UNIQUE FIELD LOCATIONS
# ============================================================

valid_df = image_gps_df[
    image_gps_df["status"] == "GPS_FOUND"
].copy()

if len(valid_df) > 0:

    # Round coordinates to 6 decimal places
    valid_df["latitude"] = valid_df["latitude"].round(6)
    valid_df["longitude"] = valid_df["longitude"].round(6)

    # Unique field coordinates
    unique_coordinates = (
        valid_df[
            ["latitude", "longitude"]
        ]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # Create field IDs
    unique_coordinates["field_id"] = [
        f"FIELD_{i:02d}"
        for i in range(
            1,
            len(unique_coordinates) + 1
        )
    ]

    # Put field_id first
    field_locations = unique_coordinates[
        [
            "field_id",
            "latitude",
            "longitude"
        ]
    ]

    # Save required field_locations.csv
    field_locations.to_csv(
        FIELD_CSV,
        index=False
    )

    print("\n" + "=" * 70)
    print("UNIQUE FIELD LOCATIONS")
    print("=" * 70)

    display(field_locations)

    print(
        "\nNumber of unique fields:",
        len(field_locations)
    )

else:

    field_locations = pd.DataFrame(
        columns=[
            "field_id",
            "latitude",
            "longitude"
        ]
    )

    print("\n❌ No GPS coordinates found.")
    print("field_locations.csv NOT created.")


# ============================================================
# SAVE REPORT
# ============================================================

report = f"""
STEP 5B — OCR GPS COORDINATE EXTRACTION REPORT
==================================================

Date:
{datetime.now()}

GPS image folder:
{GPS_FOLDER}

Total images scanned:
{total}

GPS coordinates extracted:
{gps_found}

GPS extraction failed:
{gps_failed}

Unique field locations:
{len(field_locations)}

Image GPS CSV:
{IMAGE_GPS_CSV}

Field locations CSV:
{FIELD_CSV}

NOTE:
GPS coordinates were extracted from the GPS text
embedded directly into the images using OCR.
EXIF GPS metadata was not used.
"""

REPORT_FILE.write_text(
    report,
    encoding="utf-8"
)

# ============================================================
# SAVE THIS CODE TO DRIVE
# ============================================================

# Save current notebook cell source if available
try:

    import inspect

    source = inspect.getsource(
        extract_gps_from_image
    )

except:
    source = """
Step 5B OCR GPS extraction code executed successfully.
Full code is available in the Colab notebook.
"""

CODE_FILE.write_text(
    source,
    encoding="utf-8"
)

# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 70)
print("STEP 5B — FINAL STATUS")
print("=" * 70)

if gps_found > 0:

    print("\n✅ GPS coordinates successfully extracted")
    print("✅ Unique field locations created")
    print("✅ image_gps_coordinates.csv saved")
    print("✅ field_locations.csv saved")
    print("✅ Report saved")
    print("✅ Code backup saved")

    print("\nField locations:")
    print(FIELD_CSV)

else:

    print("\n❌ GPS extraction failed")
    print("Do NOT continue to GEE yet.")

print("\n" + "=" * 70)