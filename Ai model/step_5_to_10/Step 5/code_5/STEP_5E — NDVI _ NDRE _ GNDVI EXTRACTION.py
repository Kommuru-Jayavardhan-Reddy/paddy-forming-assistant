# ============================================================
# STEP_5E — NDVI / NDRE / GNDVI EXTRACTION
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
    "clean_field_candidates_renamed.csv"
)

OUTPUT_CSV = (
    SATELLITE_FOLDER /
    "sentinel2_timeseries_raw.csv"
)

# ------------------------------------------------------------
# LOAD FINAL FIELDS
# ------------------------------------------------------------

fields = pd.read_csv(
    FIELD_CSV
)

# ------------------------------------------------------------
# SENTINEL-2
# ------------------------------------------------------------

S2 = ee.ImageCollection(
    "COPERNICUS/S2_SR_HARMONIZED"
)

START_DATE = "2026-05-01"
END_DATE = "2026-10-01"

CLOUD_LIMIT = 20
BUFFER_METERS = 50

# ------------------------------------------------------------
# RESULTS
# ------------------------------------------------------------

results = []

# ------------------------------------------------------------
# PROCESS EACH FIELD
# ------------------------------------------------------------

for _, field in fields.iterrows():

    field_id = field["field_id"]

    lat = float(field["latitude"])
    lon = float(field["longitude"])

    print("\n" + "=" * 70)
    print(field_id)
    print("Latitude :", lat)
    print("Longitude:", lon)
    print("=" * 70)

    point = ee.Geometry.Point(
        [lon, lat]
    )

    region = point.buffer(
        BUFFER_METERS
    )

    collection = (
        S2
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

    image_count = collection.size().getInfo()

    image_list = collection.toList(
        image_count
    )

    # --------------------------------------------------------
    # ONE IMAGE PER DATE
    # LOWEST CLOUD IMAGE SELECTED
    # --------------------------------------------------------

    date_dict = {}

    for i in range(image_count):

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

        if (
            date not in date_dict
            or cloud <
            date_dict[date]["cloud_percentage"]
        ):

            date_dict[date] = {
                "image": image,
                "cloud_percentage": cloud,
                "image_id": image_id
            }

    # --------------------------------------------------------
    # CALCULATE INDICES
    # --------------------------------------------------------

    for date in sorted(date_dict.keys()):

        item = date_dict[date]

        image = item["image"]

        # ----------------------------------------------------
        # SCALE SENTINEL-2 REFLECTANCE
        # ----------------------------------------------------

        image = image.select(
            [
                "B3",
                "B4",
                "B5",
                "B8"
            ]
        ).multiply(
            0.0001
        )

        # ----------------------------------------------------
        # NDVI
        # (B8 - B4) / (B8 + B4)
        # ----------------------------------------------------

        ndvi = image.normalizedDifference(
            ["B8", "B4"]
        ).rename("NDVI")

        # ----------------------------------------------------
        # NDRE
        # (B8 - B5) / (B8 + B5)
        # ----------------------------------------------------

        ndre = image.normalizedDifference(
            ["B8", "B5"]
        ).rename("NDRE")

        # ----------------------------------------------------
        # GNDVI
        # (B8 - B3) / (B8 + B3)
        # ----------------------------------------------------

        gndvi = image.normalizedDifference(
            ["B8", "B3"]
        ).rename("GNDVI")

        # ----------------------------------------------------
        # COMBINE
        # ----------------------------------------------------

        indices = ee.Image.cat(
            [
                ndvi,
                ndre,
                gndvi
            ]
        )

        # ----------------------------------------------------
        # MEAN VALUE INSIDE 50m FIELD BUFFER
        # ----------------------------------------------------

        stats = indices.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10,
            bestEffort=True,
            maxPixels=1e9
        ).getInfo()

        ndvi_value = stats.get(
            "NDVI"
        )

        ndre_value = stats.get(
            "NDRE"
        )

        gndvi_value = stats.get(
            "GNDVI"
        )

        results.append({

            "field_id":
                field_id,

            "date":
                date,

            "NDVI":
                ndvi_value,

            "NDRE":
                ndre_value,

            "GNDVI":
                gndvi_value,

            "cloud_percentage":
                item["cloud_percentage"],

            "image_id":
                item["image_id"]
        })

        print(
            f"{date} | "
            f"NDVI={ndvi_value} | "
            f"NDRE={ndre_value} | "
            f"GNDVI={gndvi_value}"
        )

# ------------------------------------------------------------
# DATAFRAME
# ------------------------------------------------------------

timeseries = pd.DataFrame(
    results
)

# ------------------------------------------------------------
# SORT
# ------------------------------------------------------------

timeseries = timeseries.sort_values(
    [
        "field_id",
        "date"
    ]
).reset_index(
    drop=True
)

# ------------------------------------------------------------
# ROUND VALUES
# ------------------------------------------------------------

for column in [
    "NDVI",
    "NDRE",
    "GNDVI"
]:

    timeseries[column] = (
        timeseries[column]
        .round(6)
    )

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

timeseries.to_csv(
    OUTPUT_CSV,
    index=False
)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 5F — VEGETATION INDEX SUMMARY")
print("=" * 70)

summary = (
    timeseries
    .groupby("field_id")
    .agg(
        dates=("date", "count"),
        NDVI_min=("NDVI", "min"),
        NDVI_max=("NDVI", "max"),
        NDRE_min=("NDRE", "min"),
        NDRE_max=("NDRE", "max"),
        GNDVI_min=("GNDVI", "min"),
        GNDVI_max=("GNDVI", "max")
    )
    .reset_index()
)

display(summary)

print("\nTotal records:", len(timeseries))

print("\nSaved to:")
print(OUTPUT_CSV)

print(
    "\n⚠️ 10-step interpolation is NOT done yet."
)

print(
    "⚠️ Original satellite values are preserved."
)

print(
    "\n✅ STEP 5F NDVI / NDRE / GNDVI COMPLETE"
)