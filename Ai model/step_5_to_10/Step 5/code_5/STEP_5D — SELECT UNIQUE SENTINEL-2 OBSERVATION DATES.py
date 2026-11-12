# ============================================================
# STEP_5D — SELECT UNIQUE SENTINEL-2 OBSERVATION DATES
# ============================================================

import ee
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# EARTH ENGINE
# ------------------------------------------------------------

EE_PROJECT = "gen-lang-client-0968273119"

ee.Initialize(
    project=EE_PROJECT
)

print("✅ Earth Engine initialized")

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

SATELLITE_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/Step 5"
)

FIELD_CSV = (
    SATELLITE_FOLDER /
    "clean_field_candidates.csv"
)

OUTPUT_CSV = (
    SATELLITE_FOLDER /
    "sentinel2_selected_dates.csv"
)

# ------------------------------------------------------------
# LOAD FINAL FIELDS
# ------------------------------------------------------------

fields = pd.read_csv(
    FIELD_CSV
)

# ------------------------------------------------------------
# SENTINEL-2 COLLECTION
# ------------------------------------------------------------

s2 = ee.ImageCollection(
    "COPERNICUS/S2_SR_HARMONIZED"
)

START_DATE = "2026-05-01"
END_DATE = "2026-10-01"

CLOUD_LIMIT = 20
BUFFER_METERS = 50

# ------------------------------------------------------------
# COLLECT UNIQUE DATES
# ------------------------------------------------------------

all_rows = []

for _, field in fields.iterrows():

    field_id = field["field_id"]

    lat = float(field["latitude"])
    lon = float(field["longitude"])

    point = ee.Geometry.Point(
        [lon, lat]
    )

    region = point.buffer(
        BUFFER_METERS
    )

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
        .sort("system:time_start")
    )

    image_list = collection.toList(
        collection.size()
    )

    count = collection.size().getInfo()

    print("\n" + "=" * 60)
    print(field_id)
    print("=" * 60)

    date_dict = {}

    for i in range(count):

        image = ee.Image(
            image_list.get(i)
        )

        date = image.date().format(
            "YYYY-MM-dd"
        ).getInfo()

        cloud = image.get(
            "CLOUDY_PIXEL_PERCENTAGE"
        ).getInfo()

        image_id = image.get(
            "PRODUCT_ID"
        ).getInfo()

        # ----------------------------------------------------
        # KEEP ONLY ONE IMAGE PER DATE
        # LOWEST CLOUD IMAGE IS SELECTED
        # ----------------------------------------------------

        if (
            date not in date_dict
            or cloud < date_dict[date]["cloud_percentage"]
        ):

            date_dict[date] = {
                "field_id": field_id,
                "date": date,
                "cloud_percentage": cloud,
                "image_id": image_id
            }

    # --------------------------------------------------------
    # SORT DATES
    # --------------------------------------------------------

    selected = sorted(
        date_dict.values(),
        key=lambda x: x["date"]
    )

    print(
        "Unique dates available:",
        len(selected)
    )

    for item in selected:

        print(
            f'{item["date"]} | '
            f'Cloud: {item["cloud_percentage"]:.2f}%'
        )

        all_rows.append(item)

# ------------------------------------------------------------
# CREATE DATAFRAME
# ------------------------------------------------------------

selected_dates = pd.DataFrame(
    all_rows
)

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

selected_dates.to_csv(
    OUTPUT_CSV,
    index=False
)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("STEP 5D — UNIQUE DATE SUMMARY")
print("=" * 60)

summary = (
    selected_dates
    .groupby("field_id")
    .agg(
        unique_dates=("date", "nunique")
    )
    .reset_index()
)

display(summary)

print("\nSaved to:")
print(OUTPUT_CSV)

print(
    "\n⚠️ Satellite images NOT exported yet."
)

print(
    "⚠️ NDVI/NDRE/GNDVI NOT calculated yet."
)

print(
    "\n✅ STEP 5D DATE SELECTION COMPLETE"
)