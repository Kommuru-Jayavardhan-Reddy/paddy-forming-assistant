# ============================================================
# STEP 5I.1— ALL 4 FIELDS PRESENTATION PNG
# RGB + NDVI + NDRE + GNDVI + TIME SERIES
# Actual 2026 Sentinel-2 Data
# ============================================================

import ee
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import requests
import os


# ------------------------------------------------------------
# 1. EARTH ENGINE
# ------------------------------------------------------------

try:
    ee.Initialize(project="gen-lang-client-0968273119")
except Exception:
    ee.Authenticate()
    ee.Initialize(project="gen-lang-client-0968273119")

print("✅ Earth Engine initialized")


# ------------------------------------------------------------
# 2. PATHS
# ONLY PATH CHANGED
# ------------------------------------------------------------

BASE = "/content/drive/MyDrive/final year project"

SATELLITE_DIR = os.path.join(
    BASE,
    "Real_world_test",
    "Step 5"
)

OUTPUT_DIR = os.path.join(
    SATELLITE_DIR,
    "presentation_png"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ------------------------------------------------------------
# 3. LOAD FIELD LOCATIONS
# ------------------------------------------------------------

field_file = os.path.join(
    SATELLITE_DIR,
    "field_locations.csv"
)

fields = pd.read_csv(field_file)

print("\nFields found:")
print(fields["field_id"].tolist())


# ------------------------------------------------------------
# 4. LOAD ACTUAL RAW SATELLITE DATA
# ------------------------------------------------------------

raw_file = os.path.join(
    SATELLITE_DIR,
    "sentinel2_timeseries_raw.csv"
)

raw_df = pd.read_csv(raw_file)

raw_df["date"] = pd.to_datetime(
    raw_df["date"]
)

print("\nRaw satellite data loaded:")
print(raw_df.shape)


# ------------------------------------------------------------
# 5. SENTINEL-2 COLLECTION
# ------------------------------------------------------------

collection = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterDate(
        "2026-05-01",
        "2026-10-01"
    )
    .filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            20
        )
    )
)


# ------------------------------------------------------------
# 6. VISUALIZATION SETTINGS
# ------------------------------------------------------------

RGB_VIS = {
    "bands": ["B4", "B3", "B2"],
    "min": 0,
    "max": 3000
}

NDVI_VIS = {
    "min": -0.2,
    "max": 0.9,
    "palette": [
        "blue",
        "white",
        "yellow",
        "green",
        "darkgreen"
    ]
}

NDRE_VIS = {
    "min": -0.2,
    "max": 0.8,
    "palette": [
        "blue",
        "white",
        "yellow",
        "green",
        "darkgreen"
    ]
}

GNDVI_VIS = {
    "min": -0.2,
    "max": 0.9,
    "palette": [
        "blue",
        "white",
        "yellow",
        "green",
        "darkgreen"
    ]
}


# ============================================================
# 7. PROCESS ALL FOUR FIELDS
# ============================================================

for FIELD_ID in fields["field_id"]:

    print("\n" + "=" * 70)
    print("PROCESSING:", FIELD_ID)
    print("=" * 70)

    # --------------------------------------------------------
    # FIELD LOCATION
    # --------------------------------------------------------

    field_row = fields[
        fields["field_id"] == FIELD_ID
    ].iloc[0]

    latitude = float(
        field_row["latitude"]
    )

    longitude = float(
        field_row["longitude"]
    )

    print("Latitude :", latitude)
    print("Longitude:", longitude)


    # --------------------------------------------------------
    # FIELD GEOMETRY
    # --------------------------------------------------------

    point = ee.Geometry.Point([
        longitude,
        latitude
    ])

    # 500 m presentation area
    region = point.buffer(500).bounds()


    # --------------------------------------------------------
    # GET ACTUAL DATES FROM RAW DATA
    # --------------------------------------------------------

    field_data = raw_df[
        raw_df["field_id"] == FIELD_ID
    ].copy()

    field_data = field_data.sort_values(
        "date"
    )

    dates = (
        field_data["date"]
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )

    print("\nDates:", len(dates))

    for d in dates:
        print(" ", d)


    # --------------------------------------------------------
    # FUNCTIONS
    # --------------------------------------------------------

    def get_image(date):

        img = (
            collection
            .filterBounds(point)
            .filterDate(
                ee.Date(date),
                ee.Date(date).advance(1, "day")
            )
            .sort(
                "CLOUDY_PIXEL_PERCENTAGE"
            )
            .first()
        )

        return img


    def get_thumbnail(img, vis_params):

        url = img.visualize(
            **vis_params
        ).getThumbURL({
            "region": region,
            "dimensions": 500,
            "format": "png"
        })

        response = requests.get(
            url,
            timeout=60
        )

        response.raise_for_status()

        return Image.open(
            BytesIO(response.content)
        ).convert("RGB")


    # --------------------------------------------------------
    # DOWNLOAD VISUALIZATIONS
    # --------------------------------------------------------

    rgb_images = []
    ndvi_images = []
    ndre_images = []
    gndvi_images = []

    valid_dates = []

    for date in dates:

        print(
            "\nDownloading:",
            date
        )

        img = get_image(date)

        if img is None:
            print(
                "⚠️ No Sentinel-2 image:",
                date
            )
            continue

        try:

            # RGB
            rgb = get_thumbnail(
                img,
                RGB_VIS
            )

            # NDVI
            ndvi = (
                img
                .normalizedDifference(
                    ["B8", "B4"]
                )
                .rename("NDVI")
            )

            ndvi_img = get_thumbnail(
                ndvi,
                NDVI_VIS
            )

            # NDRE
            ndre = (
                img
                .normalizedDifference(
                    ["B8", "B5"]
                )
                .rename("NDRE")
            )

            ndre_img = get_thumbnail(
                ndre,
                NDRE_VIS
            )

            # GNDVI
            gndvi = (
                img
                .normalizedDifference(
                    ["B8", "B3"]
                )
                .rename("GNDVI")
            )

            gndvi_img = get_thumbnail(
                gndvi,
                GNDVI_VIS
            )

            rgb_images.append(rgb)
            ndvi_images.append(ndvi_img)
            ndre_images.append(ndre_img)
            gndvi_images.append(gndvi_img)

            valid_dates.append(date)

            print("  ✅ Done")

        except Exception as e:

            print(
                "  ❌ Error:",
                e
            )


    # --------------------------------------------------------
    # CHECK
    # --------------------------------------------------------

    if len(rgb_images) == 0:

        print(
            "\n❌ No images available for",
            FIELD_ID
        )

        continue


    # --------------------------------------------------------
    # FINAL FIGURE
    # --------------------------------------------------------

    n = len(rgb_images)

    fig = plt.figure(
        figsize=(20, 15)
    )

    gs = fig.add_gridspec(
        5,
        n,
        height_ratios=[
            1,
            1,
            1,
            1,
            1.5
        ],
        hspace=0.25,
        wspace=0.08
    )


    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    fig.suptitle(
        f"Sentinel-2 Satellite Time-Series Analysis — {FIELD_ID}",
        fontsize=20,
        fontweight="bold"
    )


    # --------------------------------------------------------
    # RGB
    # --------------------------------------------------------

    for i in range(n):

        ax = fig.add_subplot(
            gs[0, i]
        )

        ax.imshow(
            rgb_images[i]
        )

        ax.set_title(
            valid_dates[i],
            fontsize=9
        )

        ax.axis("off")


    # --------------------------------------------------------
    # NDVI
    # --------------------------------------------------------

    for i in range(n):

        ax = fig.add_subplot(
            gs[1, i]
        )

        ax.imshow(
            ndvi_images[i]
        )

        ax.axis("off")


    # --------------------------------------------------------
    # NDRE
    # --------------------------------------------------------

    for i in range(n):

        ax = fig.add_subplot(
            gs[2, i]
        )

        ax.imshow(
            ndre_images[i]
        )

        ax.axis("off")


    # --------------------------------------------------------
    # GNDVI
    # --------------------------------------------------------

    for i in range(n):

        ax = fig.add_subplot(
            gs[3, i]
        )

        ax.imshow(
            gndvi_images[i]
        )

        ax.axis("off")


    # --------------------------------------------------------
    # ROW LABELS
    # --------------------------------------------------------

    fig.text(
        0.01,
        0.79,
        "RGB",
        fontsize=13,
        fontweight="bold"
    )

    fig.text(
        0.01,
        0.62,
        "NDVI",
        fontsize=13,
        fontweight="bold"
    )

    fig.text(
        0.01,
        0.44,
        "NDRE",
        fontsize=13,
        fontweight="bold"
    )

    fig.text(
        0.01,
        0.26,
        "GNDVI",
        fontsize=13,
        fontweight="bold"
    )


    # --------------------------------------------------------
    # TIME SERIES
    # --------------------------------------------------------

    ax = fig.add_subplot(
        gs[4, :]
    )

    # Use actual raw values
    plot_data = field_data[
        field_data["date"].dt.strftime(
            "%Y-%m-%d"
        ).isin(valid_dates)
    ].copy()

    # Match valid dates
    plot_data = (
        plot_data
        .drop_duplicates(
            subset=["date"]
        )
        .sort_values("date")
    )

    x = np.arange(
        len(plot_data)
    )

    ax.plot(
        x,
        plot_data["NDVI"].values,
        marker="o",
        label="NDVI"
    )

    ax.plot(
        x,
        plot_data["NDRE"].values,
        marker="o",
        label="NDRE"
    )

    ax.plot(
        x,
        plot_data["GNDVI"].values,
        marker="o",
        label="GNDVI"
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        plot_data["date"].dt.strftime(
            "%d-%b"
        ),
        rotation=45
    )

    ax.set_ylabel(
        "Index Value"
    )

    ax.set_xlabel(
        "Sentinel-2 Observation Date"
    )

    ax.set_title(
        "Vegetation Index Time Series",
        fontweight="bold"
    )

    ax.grid(
        True,
        alpha=0.3
    )

    ax.legend()


    # --------------------------------------------------------
    # LOCATION INFO
    # --------------------------------------------------------

    fig.text(
        0.72,
        0.02,
        f"{FIELD_ID}\n"
        f"Latitude: {latitude:.6f}\n"
        f"Longitude: {longitude:.6f}\n"
        f"Sentinel-2: 2026",
        fontsize=10
    )


    # --------------------------------------------------------
    # SAVE PNG
    # --------------------------------------------------------

    output_file = os.path.join(
        OUTPUT_DIR,
        f"{FIELD_ID}_Sentinel2_Presentation.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(
        "\n✅ SAVED:",
        output_file
    )


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 70)
print("🎉 STEP 5I — ALL FIELDS COMPLETED")
print("=" * 70)

print("\nOutput folder:")
print(OUTPUT_DIR)

print("\nGenerated files:")

for file in sorted(
    os.listdir(OUTPUT_DIR)
):

    print("✅", file)