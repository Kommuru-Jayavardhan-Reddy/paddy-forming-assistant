# ============================================================
# STEP 5I: SENTINEL-2 PRESENTATION PNG
# Actual 2026 Sentinel-2 Data
# FIELD_01
# RGB + NDVI + NDRE + GNDVI + Time-Series Graph
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
# 1. INITIALIZE EARTH ENGINE
# ------------------------------------------------------------

try:
    ee.Initialize(project='gen-lang-client-0968273119')
except Exception:
    ee.Authenticate()
    ee.Initialize(project='gen-lang-client-0968273119')

print("Earth Engine initialized successfully")


# ------------------------------------------------------------
# 2. DRIVE PATHS
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

print("Output folder:")
print(OUTPUT_DIR)


# ------------------------------------------------------------
# 3. LOAD OUR ACTUAL FIELD LOCATIONS
# ------------------------------------------------------------

field_file = os.path.join(
    SATELLITE_DIR,
    "field_locations.csv"
)

fields = pd.read_csv(field_file)

print("\nField locations:")
print(fields)


# ------------------------------------------------------------
# 4. SELECT FIELD_01
# ------------------------------------------------------------

FIELD_ID = "FIELD_01"

field_row = fields[
    fields["field_id"] == FIELD_ID
].iloc[0]

latitude = float(field_row["latitude"])
longitude = float(field_row["longitude"])

print("\nSelected field:", FIELD_ID)
print("Latitude :", latitude)
print("Longitude:", longitude)


# ------------------------------------------------------------
# 5. CREATE FIELD POINT
# ------------------------------------------------------------

point = ee.Geometry.Point([
    longitude,
    latitude
])

# 500 m buffer for presentation
region = point.buffer(500).bounds()


# ------------------------------------------------------------
# 6. LOAD ACTUAL SENTINEL-2 DATA
# ------------------------------------------------------------

collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(point)
    .filterDate("2026-05-01", "2026-10-01")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
)

print("\nSentinel-2 collection loaded")


# ------------------------------------------------------------
# 7. GET ACTUAL DATES FROM OUR RAW DATA
# ------------------------------------------------------------

raw_file = os.path.join(
    SATELLITE_DIR,
    "sentinel2_timeseries_raw.csv"
)

raw_df = pd.read_csv(raw_file)

field_data = raw_df[
    raw_df["field_id"] == FIELD_ID
].copy()

field_data["date"] = pd.to_datetime(
    field_data["date"]
)

field_data = field_data.sort_values("date")

dates = field_data["date"].dt.strftime(
    "%Y-%m-%d"
).tolist()

print("\nActual Sentinel-2 observation dates:")

for d in dates:
    print(d)


# ------------------------------------------------------------
# 8. DOWNLOAD SENTINEL-2 VISUALIZATIONS
# ------------------------------------------------------------

def get_sentinel_image(date):

    start = ee.Date(date)
    end = start.advance(1, "day")

    img = (
        collection
        .filterDate(start, end)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .first()
    )

    return img


def get_thumbnail(img, vis_params):

    url = img.visualize(
        **vis_params
    ).getThumbURL({
        "region": region,
        "dimensions": 700,
        "format": "png"
    })

    response = requests.get(url)

    response.raise_for_status()

    return Image.open(
        BytesIO(response.content)
    ).convert("RGB")


# ------------------------------------------------------------
# 9. VISUALIZATION SETTINGS
# ------------------------------------------------------------

rgb_vis = {
    "bands": ["B4", "B3", "B2"],
    "min": 0,
    "max": 3000
}

ndvi_vis = {
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

ndre_vis = {
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

gndvi_vis = {
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


# ------------------------------------------------------------
# 10. CREATE IMAGES FOR EACH DATE
# ------------------------------------------------------------

rgb_images = []
ndvi_images = []
ndre_images = []
gndvi_images = []

print("\nDownloading actual Sentinel-2 visualizations...")

for date in dates:

    print("Processing:", date)

    img = get_sentinel_image(date)

    if img is None:
        print("WARNING: No image found for", date)
        continue

    # RGB
    rgb = get_thumbnail(
        img,
        rgb_vis
    )

    # NDVI
    ndvi = img.normalizedDifference(
        ["B8", "B4"]
    ).rename("NDVI")

    ndvi_img = get_thumbnail(
        ndvi,
        ndvi_vis
    )

    # NDRE
    ndre = img.normalizedDifference(
        ["B8", "B5"]
    ).rename("NDRE")

    ndre_img = get_thumbnail(
        ndre,
        ndre_vis
    )

    # GNDVI
    gndvi = img.normalizedDifference(
        ["B8", "B3"]
    ).rename("GNDVI")

    gndvi_img = get_thumbnail(
        gndvi,
        gndvi_vis
    )

    rgb_images.append(rgb)
    ndvi_images.append(ndvi_img)
    ndre_images.append(ndre_img)
    gndvi_images.append(gndvi_img)


print("\nAll satellite visualizations downloaded.")


# ------------------------------------------------------------
# 11. CREATE FINAL PRESENTATION FIGURE
# ------------------------------------------------------------

n_dates = len(rgb_images)

fig = plt.figure(
    figsize=(22, 15)
)

gs = fig.add_gridspec(
    5,
    n_dates + 1,
    height_ratios=[1, 1, 1, 1, 1.5],
    width_ratios=[1] * n_dates + [1.4],
    hspace=0.25,
    wspace=0.12
)


# ------------------------------------------------------------
# 12. TITLE
# ------------------------------------------------------------

fig.suptitle(
    f"Sentinel-2 Satellite Time-Series Analysis — {FIELD_ID}",
    fontsize=20,
    fontweight="bold"
)


# ------------------------------------------------------------
# 13. RGB ROW
# ------------------------------------------------------------

for i in range(n_dates):

    ax = fig.add_subplot(
        gs[0, i]
    )

    ax.imshow(
        rgb_images[i]
    )

    ax.set_title(
        dates[i],
        fontsize=10
    )

    ax.axis("off")


# ------------------------------------------------------------
# 14. NDVI ROW
# ------------------------------------------------------------

for i in range(n_dates):

    ax = fig.add_subplot(
        gs[1, i]
    )

    ax.imshow(
        ndvi_images[i]
    )

    ax.axis("off")


# ------------------------------------------------------------
# 15. NDRE ROW
# ------------------------------------------------------------

for i in range(n_dates):

    ax = fig.add_subplot(
        gs[2, i]
    )

    ax.imshow(
        ndre_images[i]
    )

    ax.axis("off")


# ------------------------------------------------------------
# 16. GNDVI ROW
# ------------------------------------------------------------

for i in range(n_dates):

    ax = fig.add_subplot(
        gs[3, i]
    )

    ax.imshow(
        gndvi_images[i]
    )

    ax.axis("off")


# ------------------------------------------------------------
# 17. ROW LABELS
# ------------------------------------------------------------

row_labels = [
    "RGB\n(Sentinel-2)",
    "NDVI",
    "NDRE",
    "GNDVI"
]

for row, label in enumerate(row_labels):

    ax = fig.add_subplot(
        gs[row, -1]
    )

    ax.text(
        0.5,
        0.5,
        label,
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold"
    )

    ax.axis("off")


# ------------------------------------------------------------
# 18. TIME-SERIES GRAPH
# ------------------------------------------------------------

ax_graph = fig.add_subplot(
    gs[4, :]
)

x = np.arange(
    len(field_data)
)

ax_graph.plot(
    x,
    field_data["NDVI"].values,
    marker="o",
    label="NDVI"
)

ax_graph.plot(
    x,
    field_data["NDRE"].values,
    marker="o",
    label="NDRE"
)

ax_graph.plot(
    x,
    field_data["GNDVI"].values,
    marker="o",
    label="GNDVI"
)

ax_graph.set_xticks(x)

ax_graph.set_xticklabels(
    field_data["date"].dt.strftime("%d-%b"),
    rotation=45
)

ax_graph.set_ylabel(
    "Index Value"
)

ax_graph.set_xlabel(
    "Sentinel-2 Observation Date"
)

ax_graph.set_title(
    "Vegetation Index Time Series",
    fontweight="bold"
)

ax_graph.grid(
    True,
    alpha=0.3
)

ax_graph.legend()


# ------------------------------------------------------------
# 19. FIELD LOCATION INFORMATION
# ------------------------------------------------------------

fig.text(
    0.02,
    0.02,
    f"Field Location: {FIELD_ID}\n"
    f"Latitude: {latitude:.6f}\n"
    f"Longitude: {longitude:.6f}\n"
    f"Data Source: Sentinel-2 SR Harmonized\n"
    f"Period: May–September 2026",
    fontsize=11
)


# ------------------------------------------------------------
# 20. SAVE FINAL PNG
# ------------------------------------------------------------

output_file = os.path.join(
    OUTPUT_DIR,
    f"{FIELD_ID}_Sentinel2_Presentation.png"
)

plt.savefig(
    output_file,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("\n======================================")
print("STEP 5I COMPLETED")
print("======================================")
print("PNG saved at:")
print(output_file)