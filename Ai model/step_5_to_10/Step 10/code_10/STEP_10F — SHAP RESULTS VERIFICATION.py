# ================================================================
# STEP 10F — SHAP RESULTS VERIFICATION
# Paddy Farming Assistant
# ================================================================

import numpy as np
import pandas as pd
from pathlib import Path

print("=" * 70)
print("STEP 10F — SHAP RESULTS VERIFICATION")
print("=" * 70)

# ------------------------------------------------
# 1. FILE PATHS
# ------------------------------------------------

OUTPUT_DIR = Path(
    "/content/drive/MyDrive/final year project/AI_model/"
    "step_5_to_9/Step 8/SHAP_Results"
)

SUMMARY_PATH = OUTPUT_DIR / (
    "step10E_balanced_validation_shap_summary.csv"
)

SHAP_PATH = OUTPUT_DIR / (
    "step10E_balanced_validation_shap_values.npy"
)

IMPORTANCE_PATH = OUTPUT_DIR / (
    "step10E_balanced_feature_importance.csv"
)

# ------------------------------------------------
# 2. CHECK FILES
# ------------------------------------------------

files = {
    "Summary CSV": SUMMARY_PATH,
    "SHAP values": SHAP_PATH,
    "Feature importance CSV": IMPORTANCE_PATH
}

for name, path in files.items():
    print(f"{name}: {'EXISTS' if path.exists() else 'MISSING'}")

if not all(path.exists() for path in files.values()):
    raise FileNotFoundError(
        "One or more STEP 10E result files are missing."
    )

# ------------------------------------------------
# 3. LOAD RESULTS
# ------------------------------------------------

summary_df = pd.read_csv(SUMMARY_PATH)
shap_values = np.load(SHAP_PATH)
importance_df = pd.read_csv(IMPORTANCE_PATH)

print("\nSummary shape:", summary_df.shape)
print("SHAP shape:", shap_values.shape)
print("Importance shape:", importance_df.shape)

# ------------------------------------------------
# 4. VERIFY SHAP DIMENSIONS
# ------------------------------------------------

assert shap_values.ndim == 3, (
    "SHAP array must have 3 dimensions."
)

assert shap_values.shape[1:] == (10, 3), (
    "Expected SHAP dimensions: (samples, 10, 3)."
)

assert len(summary_df) == shap_values.shape[0], (
    "Summary sample count does not match SHAP array."
)

assert np.isfinite(shap_values).all(), (
    "SHAP array contains NaN or infinite values."
)

print("\nPASS: SHAP dimensions and numerical values are valid.")

# ------------------------------------------------
# 5. VERIFY CLASS COVERAGE
# ------------------------------------------------

class_counts = summary_df["true_label"].value_counts().sort_index()

print("\nDisease class coverage:")
print(class_counts.to_string())

expected_classes = set(range(11))
observed_classes = set(summary_df["true_label"].astype(int))

missing_classes = sorted(expected_classes - observed_classes)

if missing_classes:
    print("\nWARNING: Missing classes:", missing_classes)
else:
    print("\nPASS: All 11 classes are represented.")

# ------------------------------------------------
# 6. RECOMPUTE FEATURE IMPORTANCE
# ------------------------------------------------

feature_names = ["NDVI", "NDRE", "GNDVI"]

recomputed = np.mean(
    np.abs(shap_values),
    axis=(0, 1)
)

recomputed_df = pd.DataFrame({
    "Satellite_Feature": feature_names,
    "Recomputed_Mean_Absolute_SHAP": recomputed
}).sort_values(
    "Recomputed_Mean_Absolute_SHAP",
    ascending=False
)

print("\nRecomputed feature importance:")
print(recomputed_df.to_string(index=False))

# Compare saved values with recomputed values.
saved_values = importance_df.set_index(
    "Satellite_Feature"
)["Mean_Absolute_SHAP"]

for feature, value in zip(feature_names, recomputed):
    if feature not in saved_values.index:
        raise ValueError(
            f"Feature {feature} is missing from saved importance CSV."
        )

    if not np.isclose(
        value,
        saved_values.loc[feature],
        rtol=1e-5,
        atol=1e-7
    ):
        raise ValueError(
            f"Importance mismatch for {feature}: "
            f"saved={saved_values.loc[feature]}, "
            f"recomputed={value}"
        )

print("\nPASS: Saved feature importance matches SHAP arrays.")

# ------------------------------------------------
# 7. SAVE VERIFICATION REPORT
# ------------------------------------------------

report_path = OUTPUT_DIR / (
    "step10F_shap_verification_report.txt"
)

with open(report_path, "w") as f:
    f.write("STEP 10F — SHAP RESULTS VERIFICATION\n")
    f.write("=" * 50 + "\n")
    f.write(f"Samples analysed: {shap_values.shape[0]}\n")
    f.write(f"SHAP array shape: {shap_values.shape}\n")
    f.write(f"All values finite: {np.isfinite(shap_values).all()}\n")
    f.write(f"Classes represented: {len(observed_classes)}/11\n\n")
    f.write("Feature importance:\n")
    f.write(recomputed_df.to_string(index=False))
    f.write("\n")

print("\nVerification report saved:")
print(report_path)

print("\n" + "=" * 70)
print("STEP 10F VERIFICATION COMPLETED")
print("=" * 70)