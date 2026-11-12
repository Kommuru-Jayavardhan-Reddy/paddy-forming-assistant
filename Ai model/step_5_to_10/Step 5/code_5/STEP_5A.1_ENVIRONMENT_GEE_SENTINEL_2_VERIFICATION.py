# ============================================================
# STEP 5A.1 — ENVIRONMENT + GEE + SENTINEL-2 VERIFICATION
# ============================================================

from google.colab import drive
from pathlib import Path
import ee

# 1. Mount Google Drive
drive.mount("/content/drive")

# 2. Project directories
PROJECT_ROOT = Path(
    "/content/drive/MyDrive/final year project"
)

SATELLITE_DIR = PROJECT_ROOT / "satellite_data"
IMAGES_DIR = SATELLITE_DIR / "sentinel2_images"

SATELLITE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

IMAGES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# 3. Earth Engine authentication
# Run only if the current Colab session is not authenticated:
# ee.Authenticate()

# 4. Initialize Earth Engine
EE_PROJECT = "gen-lang-client-0968273119"

ee.Initialize(
    project=EE_PROJECT
)

# 5. Sentinel-2 collection
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

s2 = ee.ImageCollection(
    S2_COLLECTION
)

# 6. Required project date range
test_collection = (
    s2
    .filterDate(
        "2026-05-01",
        "2026-10-01"
    )
)

# 7. Verify collection access
count = (
    test_collection
    .size()
    .getInfo()
)

print("=" * 60)
print("STEP 5A — SENTINEL-2 COLLECTION CHECK")
print("=" * 60)

print("Collection:", S2_COLLECTION)
print("Date range: 2026-05-01 → 2026-10-01")
print("Images available:", count)

print("=" * 60)
print("STEP 5A SENTINEL-2 CHECK COMPLETE")
print("=" * 60)