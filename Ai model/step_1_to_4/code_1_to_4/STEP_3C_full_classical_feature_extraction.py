# STEP 3C: Full Classical Feature Extraction

import cv2
import numpy as np
from skimage.feature import local_binary_pattern, hog
from tqdm.auto import tqdm

def extract_features(image_path):
    # Read image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    # BGR -> RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Resize
    image = cv2.resize(image, (64, 64))

    # --------------------------------------------------
    # HSV FEATURES
    # --------------------------------------------------
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

    h_hist = cv2.calcHist(
        [hsv], [0], None, [64], [0, 180]
    ).flatten()

    s_hist = cv2.calcHist(
        [hsv], [1], None, [64], [0, 256]
    ).flatten()

    v_hist = cv2.calcHist(
        [hsv], [2], None, [64], [0, 256]
    ).flatten()

    h_hist /= (h_hist.sum() + 1e-8)
    s_hist /= (s_hist.sum() + 1e-8)
    v_hist /= (v_hist.sum() + 1e-8)

    hsv_features = np.concatenate([
        h_hist,
        s_hist,
        v_hist
    ])

    # --------------------------------------------------
    # LBP FEATURES
    # --------------------------------------------------
    gray = cv2.cvtColor(
        image,
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

    lbp_features = lbp_hist.astype(np.float32)
    lbp_features /= (lbp_features.sum() + 1e-8)

    # --------------------------------------------------
    # HOG FEATURES
    # --------------------------------------------------
    hog_features = hog(
        gray,
        orientations=9,
        pixels_per_cell=(8, 8),
        cells_per_block=(2, 2),
        block_norm="L2-Hys"
    )

    # --------------------------------------------------
    # COMBINE
    # --------------------------------------------------
    features = np.concatenate([
        hsv_features,
        lbp_features,
        hog_features
    ]).astype(np.float32)

    return features


def extract_dataset_features(image_paths, dataset_name):
    features = []
    valid_paths = []

    print(f"\nExtracting {dataset_name} features...")
    print(f"Images: {len(image_paths)}")

    for path in tqdm(
        image_paths,
        desc=dataset_name
    ):
        try:
            feat = extract_features(path)
            features.append(feat)
            valid_paths.append(path)

        except Exception as e:
            print(f"\nSkipping: {path}")
            print("Reason:", e)

    return np.array(features, dtype=np.float32), valid_paths


# --------------------------------------------------
# EXTRACT ALL THREE SETS
# --------------------------------------------------

X_train_ml, train_valid_paths = extract_dataset_features(
    X_train,
    "TRAIN"
)

X_val_ml, val_valid_paths = extract_dataset_features(
    X_val,
    "VALIDATION"
)

X_test_ml, test_valid_paths = extract_dataset_features(
    X_test,
    "TEST"
)

print("\n" + "=" * 60)
print("FULL FEATURE EXTRACTION COMPLETE")
print("=" * 60)

print("X_train_ml shape:", X_train_ml.shape)
print("X_val_ml shape  :", X_val_ml.shape)
print("X_test_ml shape :", X_test_ml.shape)

print("=" * 60)