# ============================================================
# STEP 5C.5 — SENTINEL-2 AVAILABILITY CHECK FOR 4 FIELDS
# ============================================================

import ee
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# EARTH ENGINE INITIALIZATION
# ------------------------------------------------------------

EE_PROJECT = "gen-lang-client-0968273119"

ee.Initialize(project=EE_PROJECT)

print("✅ Earth Engine initialized")

# ------------------------------------------------------------
# PATH
# ------------------------------------------------------------

SATELLITE_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/Step 5"
)

FIELD_CSV = (
    SATELLITE_FOLDER /
    "clean_field_candidates.csv"
)

# ------------------------------------------------------------
# LOAD FINAL FIELDS
# ------------------------------------------------------------

fields = pd.read_csv(FIELD_CSV)

print("\nFinal fields:")
display(fields)

# ------------------------------------------------------------
# SENTINEL-2 COLLECTION
# ------------------------------------------------------------

S2_COLLECTION = (
    "COPERNICUS/S2_SR_HARMONIZED"
)

s2 = ee.ImageCollection(
    S2_COLLECTION
)

# ------------------------------------------------------------
# SEARCH PARAMETERS
# ------------------------------------------------------------

START_DATE = "2026-05-01"
END_DATE = "2026-10-01"

CLOUD_LIMIT = 20

BUFFER_METERS = 50

# ------------------------------------------------------------
# SEARCH EACH FIELD
# ------------------------------------------------------------

results = []

for _, row in fields.iterrows():

    field_id = row["field_id"]

    lat = float(row["latitude"])
    lon = float(row["longitude"])

    # Create field point
    point = ee.Geometry.Point(
        [lon, lat]
    )

    # 50 metre buffer
    region = point.buffer(
        BUFFER_METERS
    )

    # Sentinel-2 filtering
    collection = (
        s2
        .filterBounds(region)
        .filterDate(
            START_DATE,
            END_DATE
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                CLOUD_LIMIT
            )
        )
    )

    count = collection.size().getInfo()

    # Get dates and cloud percentages
    image_info = collection.map(
        lambda img: img.set(
            "date_string",
            img.date().format("YYYY-MM-dd")
        )
    ).aggregate_array(
        "date_string"
    ).getInfo()

    cloud_info = collection.aggregate_array(
        "CLOUDY_PIXEL_PERCENTAGE"
    ).getInfo()

    print("\n" + "=" * 60)
    print(field_id)
    print("=" * 60)

    print("Latitude :", lat)
    print("Longitude:", lon)
    print("Images   :", count)

    if count > 0:

        print("Dates:")

        for date, cloud in zip(
            image_info,
            cloud_info
        ):
            print(
                f"  {date} | Cloud: {cloud:.2f}%"
            )

    else:
        print("⚠️ No Sentinel-2 images found")

    results.append({

        "field_id": field_id,

        "latitude": lat,

        "longitude": lon,

        "sentinel2_image_count": count,

        "dates": ";".join(
            sorted(set(image_info))
        )
    })

# ------------------------------------------------------------
# SAVE RESULT
# ------------------------------------------------------------

availability_df = pd.DataFrame(
    results
)

OUTPUT_CSV = (
    SATELLITE_FOLDER /
    "sentinel2_availability.csv"
)

availability_df.to_csv(
    OUTPUT_CSV,
    index=False
)

# ------------------------------------------------------------
# FINAL DISPLAY
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("STEP 5C — SENTINEL-2 AVAILABILITY SUMMARY")
print("=" * 60)

display(
    availability_df[
        [
            "field_id",
            "latitude",
            "longitude",
            "sentinel2_image_count"
        ]
    ]
)

print("\nSaved to:")
print(OUTPUT_CSV)

print("\n✅ STEP 5C AVAILABILITY CHECK COMPLETE")