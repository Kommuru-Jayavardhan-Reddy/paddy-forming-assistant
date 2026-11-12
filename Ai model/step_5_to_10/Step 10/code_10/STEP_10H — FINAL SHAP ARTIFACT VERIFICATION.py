
# ================================================================
# STEP 10H — FINAL SHAP ARTIFACT VERIFICATION
# Paddy Farming Assistant
# ================================================================

import numpy as np
import pandas as pd
from pathlib import Path

print("=" * 70)
print("STEP 10H — FINAL SHAP VERIFICATION")
print("=" * 70)

# ------------------------------------------------
# 1. OUTPUT DIRECTORY
# ------------------------------------------------

OUT = Path(
    "/content/drive/MyDrive/final year project/AI_model/"
    "step_5_to_9/Step 8/SHAP_Results"
)

if not OUT.exists():
    raise FileNotFoundError(
        f"SHAP output directory not found: {OUT}"
    )

# ------------------------------------------------
# 2. EXPECTED ARTIFACTS
# ------------------------------------------------

expected_files = [
    "shap_values_sample_0.npy",
    "shap_values_sample_0.csv",
    "shap_feature_importance_sample_0.png",
    "shap_satellite_heatmap_sample_0.png",
    "step10E_balanced_validation_shap_summary.csv",
    "step10E_balanced_validation_shap_values.npy",
    "step10E_balanced_feature_importance.csv",
    "step10E_balanced_feature_importance.png",
    "step10F_shap_verification_report.txt",
    "step10G_final_feature_importance.png",
    "step10G_timestep_feature_heatmap.png",
    "step10G_classwise_feature_importance.png",
    "step10G_final_feature_importance.csv",
    "step10G_classwise_feature_importance.csv",
    "step10G_final_shap_report.txt"
]

# ------------------------------------------------
# 3. CHECK FILE EXISTENCE
# ------------------------------------------------

file_results = []

for filename in expected_files:

    path = OUT / filename
    exists = path.is_file()

    file_results.append({
        "File": filename,
        "Status": "PASS" if exists else "MISSING",
        "Size_KB": (
            round(path.stat().st_size / 1024, 2)
            if exists else None
        )
    })

files_df = pd.DataFrame(file_results)

print("\n[1] ARTIFACT CHECK")
display(files_df)

missing_files = files_df.loc[
    files_df["Status"] == "MISSING",
    "File"
].tolist()

if missing_files:
    print("\nWARNING — Missing files:")
    for filename in missing_files:
        print(" -", filename)
else:
    print("\nPASS: All expected artifacts exist.")

# ------------------------------------------------
# 4. CHECK REQUIRED DATA FILES
# ------------------------------------------------

shap_path = OUT / (
    "step10E_balanced_validation_shap_values.npy"
)

summary_path = OUT / (
    "step10E_balanced_validation_shap_summary.csv"
)

importance_path = OUT / (
    "step10E_balanced_feature_importance.csv"
)

required_data_files = [
    shap_path,
    summary_path,
    importance_path
]

missing_data_files = [
    str(path)
    for path in required_data_files
    if not path.is_file()
]

if missing_data_files:
    raise FileNotFoundError(
        "Cannot continue verification. Missing required data files:\n"
        + "\n".join(missing_data_files)
    )

# ------------------------------------------------
# 5. LOAD SHAP RESULTS
# ------------------------------------------------

shap_values = np.load(shap_path)
summary = pd.read_csv(summary_path)
importance = pd.read_csv(importance_path)

print("\n[2] SHAP DATA CHECK")
print("Summary shape:", summary.shape)
print("SHAP shape:", shap_values.shape)
print("Importance shape:", importance.shape)

# ------------------------------------------------
# 6. VERIFY SHAP DIMENSIONS AND VALUES
# ------------------------------------------------

shape_valid = (
    shap_values.ndim == 3
    and shap_values.shape[1:] == (10, 3)
)

if not shape_valid:
    raise ValueError(
        f"Unexpected SHAP dimensions: {shap_values.shape}. "
        "Expected (number_of_samples, 10, 3)."
    )

if len(summary) != shap_values.shape[0]:
    raise ValueError(
        "Summary CSV sample count does not match SHAP array."
    )

if not np.isfinite(shap_values).all():
    raise ValueError(
        "SHAP array contains NaN or infinite values."
    )

print("\nPASS: SHAP dimensions and numerical values are valid.")
print("Validated SHAP shape:", shap_values.shape)

# ------------------------------------------------
# 7. VERIFY FEATURE IMPORTANCE
# ------------------------------------------------

feature_names = ["NDVI", "NDRE", "GNDVI"]

required_importance_columns = [
    "Satellite_Feature",
    "Mean_Absolute_SHAP"
]

missing_importance_columns = [
    col for col in required_importance_columns
    if col not in importance.columns
]

if missing_importance_columns:
    raise ValueError(
        "Missing feature-importance columns: "
        f"{missing_importance_columns}"
    )

recomputed_importance = np.mean(
    np.abs(shap_values),
    axis=(0, 1)
)

saved_importance = importance.set_index(
    "Satellite_Feature"
)["Mean_Absolute_SHAP"]

for feature, value in zip(
    feature_names,
    recomputed_importance
):

    if feature not in saved_importance.index:
        raise ValueError(
            f"Feature missing from importance CSV: {feature}"
        )

    saved_value = float(saved_importance.loc[feature])

    if not np.isclose(
        value,
        saved_value,
        rtol=1e-5,
        atol=1e-7
    ):
        raise ValueError(
            f"Importance mismatch for {feature}: "
            f"recomputed={value:.8f}, saved={saved_value:.8f}"
        )

importance_check_df = pd.DataFrame({
    "Feature": feature_names,
    "Recomputed_SHAP": recomputed_importance,
    "Saved_SHAP": [
        float(saved_importance.loc[f])
        for f in feature_names
    ],
    "Status": ["PASS"] * len(feature_names)
})

print("\n[3] FEATURE IMPORTANCE VERIFICATION")
display(importance_check_df)

print("PASS: Saved feature importance matches SHAP values.")

# ------------------------------------------------
# 8. VERIFY ALL 11 DISEASE CLASSES
# ------------------------------------------------

if "true_label" not in summary.columns:
    raise ValueError(
        "Summary CSV does not contain true_label."
    )

if summary["true_label"].isna().any():
    raise ValueError(
        "Summary CSV contains missing disease labels."
    )

classes = sorted(
    summary["true_label"].astype(int).unique().tolist()
)

expected_classes = list(range(11))

class_counts = (
    summary["true_label"]
    .astype(int)
    .value_counts()
    .sort_index()
)

print("\n[4] DISEASE CLASS COVERAGE")
print(class_counts.to_string())

if classes == expected_classes:
    print("\nPASS: All 11 disease classes are represented.")
else:
    print("\nWARNING: Expected classes 0–10.")
    print("Observed classes:", classes)

# ------------------------------------------------
# 9. VERIFY FINAL REPORT CONTENT
# ------------------------------------------------

report_path = OUT / "step10G_final_shap_report.txt"

report_exists = report_path.is_file()
report_readable = False
has_feature_importance = False
has_limitations = False

if report_exists:

    report_text = report_path.read_text(
        encoding="utf-8"
    )

    report_lower = report_text.lower()

    report_readable = True

    # Case-insensitive substring checks.
    # "Overall feature importance" also matches this check.
    has_feature_importance = (
        "feature importance" in report_lower
    )

    has_limitations = (
        "limitations" in report_lower
    )

print("\n[5] REPORT CONTENT VERIFICATION")
print(
    "Report exists:",
    "PASS" if report_exists else "FAIL"
)
print(
    "Report readable:",
    "PASS" if report_readable else "FAIL"
)
print(
    "Feature importance section:",
    "PASS" if has_feature_importance else "CHECK"
)
print(
    "Limitations section:",
    "PASS" if has_limitations else "CHECK"
)

if report_exists and (
    not has_feature_importance or not has_limitations
):
    print("\nActual report content:")
    print(report_text)

# ------------------------------------------------
# 10. VERIFY CLASS-WISE REPORT FILE
# ------------------------------------------------

class_csv_path = OUT / (
    "step10G_classwise_feature_importance.csv"
)

classwise_valid = False

if class_csv_path.is_file():

    classwise_df = pd.read_csv(class_csv_path)

    expected_classwise_columns = [
        "Class_ID",
        "Sample_Count",
        "NDVI",
        "NDRE",
        "GNDVI"
    ]

    classwise_valid = (
        all(
            col in classwise_df.columns
            for col in expected_classwise_columns
        )
        and len(classwise_df) == 11
        and set(
            classwise_df["Class_ID"].astype(int)
        ) == set(range(11))
    )

print("\n[6] CLASS-WISE RESULTS")
print(
    "Class-wise CSV verification:",
    "PASS" if classwise_valid else "CHECK"
)

# ------------------------------------------------
# 11. SAVE FINAL VERIFICATION REPORT
# ------------------------------------------------

verification_path = OUT / (
    "step10H_final_verification_report.txt"
)

verification_items = {
    "All expected artifact files exist": not missing_files,
    "SHAP dimensions valid": shape_valid,
    "SHAP values finite": bool(np.isfinite(shap_values).all()),
    "Summary count matches SHAP count": (
        len(summary) == shap_values.shape[0]
    ),
    "Feature importance verified": True,
    "All 11 disease classes represented": (
        classes == expected_classes
    ),
    "Final report exists and is readable": (
        report_exists and report_readable
    ),
    "Feature importance report section exists": (
        has_feature_importance
    ),
    "Limitations section exists": has_limitations,
    "Class-wise CSV verified": classwise_valid
}

with open(
    verification_path,
    "w",
    encoding="utf-8"
) as f:

    f.write("PADDY FARMING ASSISTANT\n")
    f.write("STEP 10H — FINAL SHAP VERIFICATION\n")
    f.write("=" * 55 + "\n\n")

    for item, passed in verification_items.items():
        f.write(
            f"{item}: {'PASS' if passed else 'CHECK'}\n"
        )

    f.write("\nSHAP array shape: ")
    f.write(str(shap_values.shape) + "\n")

    f.write("\nFeature importance:\n")
    for feature, value in zip(
        feature_names,
        recomputed_importance
    ):
        f.write(f"{feature}: {value:.8f}\n")

    f.write("\nNote: This verifies saved SHAP artifacts, ")
    f.write("not disease-classification accuracy.\n")

# ------------------------------------------------
# 12. FINAL STATUS
# ------------------------------------------------

all_checks_passed = all(
    verification_items.values()
)

print("\n" + "=" * 70)

if all_checks_passed:
    print("STEP 10H — ALL SHAP VERIFICATIONS PASSED")
else:
    print("STEP 10H — COMPLETED WITH ITEMS TO CHECK")

    for item, passed in verification_items.items():
        if not passed:
            print("CHECK:", item)

print("=" * 70)

print("\nFinal verification report:")
print(verification_path)

print("\nSHAP results directory:")
print(OUT)

