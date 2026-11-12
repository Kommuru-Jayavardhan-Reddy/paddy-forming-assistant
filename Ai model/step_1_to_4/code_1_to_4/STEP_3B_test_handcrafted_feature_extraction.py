# STEP 3B: Test Hand-Crafted Feature Extraction

import cv2
import numpy as np
from skimage.feature import local_binary_pattern, hog
from PIL import Image

# Use one training image
sample_path = X_train[0]

# Read image
image = cv2.imread(sample_path)

# Convert BGR -> RGB
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Resize
image_rgb = cv2.resize(image_rgb, (64, 64))

# --------------------------------------------------
# 1. HSV HISTOGRAM
# --------------------------------------------------

hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)

h_hist = cv2.calcHist(
    [hsv], [0], None, [64], [0, 180]
).flatten()

s_hist = cv2.calcHist(
    [hsv], [1], None, [64], [0, 256]
).flatten()

v_hist = cv2.calcHist(
    [hsv], [2], None, [64], [0, 256]
).flatten()

# Normalize histograms
h_hist = h_hist / (h_hist.sum() + 1e-8)
s_hist = s_hist / (s_hist.sum() + 1e-8)
v_hist = v_hist / (v_hist.sum() + 1e-8)

hsv_features = np.concatenate([
    h_hist,
    s_hist,
    v_hist
])

# --------------------------------------------------
# 2. LBP TEXTURE
# --------------------------------------------------

gray = cv2.cvtColor(
    image_rgb,
    cv2.COLOR_RGB2GRAY
)

P = 24
R = 3

lbp = local_binary_pattern(
    gray,
    P,
    R,
    method="uniform"
)

n_bins = P + 2

lbp_hist, _ = np.histogram(
    lbp.ravel(),
    bins=n_bins,
    range=(0, n_bins)
)

lbp_hist = lbp_hist.astype(np.float32)
lbp_hist /= (lbp_hist.sum() + 1e-8)

# --------------------------------------------------
# 3. HOG SHAPE / EDGE
# --------------------------------------------------

hog_features = hog(
    gray,
    orientations=9,
    pixels_per_cell=(8, 8),
    cells_per_block=(2, 2),
    block_norm="L2-Hys"
)

# --------------------------------------------------
# 4. COMBINE FEATURES
# --------------------------------------------------

combined_features = np.concatenate([
    hsv_features,
    lbp_hist,
    hog_features
])

print("=" * 60)
print("FEATURE EXTRACTION TEST")
print("=" * 60)

print("Sample image:")
print(sample_path)

print("\nHSV features :", len(hsv_features))
print("LBP features :", len(lbp_hist))
print("HOG features :", len(hog_features))
print("-" * 60)
print("TOTAL FEATURES:", len(combined_features))

print("=" * 60)
