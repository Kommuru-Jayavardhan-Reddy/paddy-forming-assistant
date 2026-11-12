# ================================================================
# STEP 10G — FINAL SHAP REPORT AND VISUALIZATIONS
# ================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("=" * 70)
print("STEP 10G — FINAL SHAP REPORT")
print("=" * 70)

# ------------------------------------------------
# 1. PATHS
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

# ------------------------------------------------
# 2. LOAD VERIFIED RESULTS
# ------------------------------------------------

summary_df = pd.read_csv(SUMMARY_PATH)
shap_values = np.load(SHAP_PATH)

feature_names = ["NDVI", "NDRE", "GNDVI"]

assert shap_values.shape == (len(summary_df), 10, 3)
assert np.isfinite(shap_values).all()

print("Samples:", len(summary_df))
print("SHAP shape:", shap_values.shape)

# ------------------------------------------------
# 3. OVERALL FEATURE IMPORTANCE
# ------------------------------------------------

overall_importance = np.mean(
    np.abs(shap_values),
    axis=(0, 1)
)

importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Mean_Absolute_SHAP": overall_importance
}).sort_values(
    "Mean_Absolute_SHAP",
    ascending=False
)

# Save CSV
importance_path = OUTPUT_DIR / (
    "step10G_final_feature_importance.csv"
)

importance_df.to_csv(importance_path, index=False)

# Plot
plt.figure(figsize=(8, 5))

plt.bar(
    importance_df["Feature"],
    importance_df["Mean_Absolute_SHAP"]
)

plt.title("Satellite Feature Importance — SHAP")
plt.xlabel("Satellite Feature")
plt.ylabel("Mean Absolute SHAP Value")

plt.tight_layout()

feature_plot = OUTPUT_DIR / (
    "step10G_final_feature_importance.png"
)

plt.savefig(feature_plot, dpi=300, bbox_inches="tight")
plt.show()

# ------------------------------------------------
# 4. TIMESTEP-WISE SHAP HEATMAP
# ------------------------------------------------

timestep_importance = np.mean(
    np.abs(shap_values),
    axis=0
)

plt.figure(figsize=(10, 6))

plt.imshow(
    timestep_importance.T,
    aspect="auto",
    interpolation="nearest"
)

plt.colorbar(label="Mean Absolute SHAP Value")

plt.xticks(
    ticks=np.arange(10),
    labels=[f"T{i+1}" for i in range(10)]
)

plt.yticks(
    ticks=np.arange(3),
    labels=feature_names
)

plt.xlabel("Satellite Timestep")
plt.ylabel("Satellite Feature")
plt.title("SHAP Importance Across Satellite Timesteps")

plt.tight_layout()

heatmap_path = OUTPUT_DIR / (
    "step10G_timestep_feature_heatmap.png"
)

plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
plt.show()

# ------------------------------------------------
# 5. DISEASE-CLASS-WISE FEATURE IMPORTANCE
# ------------------------------------------------

class_rows = []

for class_id in sorted(summary_df["true_label"].unique()):

    indices = np.where(
        summary_df["true_label"].to_numpy() == class_id
    )[0]

    class_shap = shap_values[indices]

    class_importance = np.mean(
        np.abs(class_shap),
        axis=(0, 1)
    )

    class_rows.append({
        "Class_ID": int(class_id),
        "Sample_Count": len(indices),
        "NDVI": class_importance[0],
        "NDRE": class_importance[1],
        "GNDVI": class_importance[2]
    })

class_importance_df = pd.DataFrame(class_rows)

class_csv = OUTPUT_DIR / (
    "step10G_classwise_feature_importance.csv"
)

class_importance_df.to_csv(class_csv, index=False)

# Plot class-wise GNDVI, NDRE and NDVI values.
plt.figure(figsize=(12, 6))

for feature in feature_names:
    plt.plot(
        class_importance_df["Class_ID"],
        class_importance_df[feature],
        marker="o",
        label=feature
    )

plt.xlabel("Disease Class ID")
plt.ylabel("Mean Absolute SHAP Value")
plt.title("Satellite Feature Importance by Disease Class")
plt.xticks(sorted(summary_df["true_label"].unique()))
plt.legend()
plt.tight_layout()

class_plot = OUTPUT_DIR / (
    "step10G_classwise_feature_importance.png"
)

plt.savefig(class_plot, dpi=300, bbox_inches="tight")
plt.show()

# ------------------------------------------------
# 6. FINAL REPORT
# ------------------------------------------------

report_path = OUTPUT_DIR / (
    "step10G_final_shap_report.txt"
)

top_feature = importance_df.iloc[0]["Feature"]
top_value = importance_df.iloc[0]["Mean_Absolute_SHAP"]

with open(report_path, "w") as f:

    f.write("PADDY FARMING ASSISTANT\n")
    f.write("STEP 10G — FINAL SHAP ANALYSIS REPORT\n")
    f.write("=" * 55 + "\n\n")

    f.write("Analysis details\n")
    f.write("-" * 30 + "\n")
    f.write(f"Validation samples analysed: {len(summary_df)}\n")
    f.write("Disease classes represented: ")
    f.write(f"{summary_df['true_label'].nunique()}/11\n")
    f.write("Satellite features: NDVI, NDRE, GNDVI\n")
    f.write("Timesteps per sequence: 10\n\n")

    f.write("Overall feature importance\n")
    f.write("-" * 30 + "\n")
    f.write(importance_df.to_string(index=False))
    f.write("\n\n")

    f.write(
        f"Highest mean absolute SHAP feature: {top_feature}\n"
    )
    f.write(
        f"Mean absolute SHAP value: {top_value:.6f}\n\n"
    )

    f.write("Interpretation and limitations\n")
    f.write("-" * 30 + "\n")
    f.write(
        "These results summarize SHAP values for the selected "
        "balanced validation samples. Mean absolute SHAP values "
        "indicate attribution magnitude, not disease detection "
        "accuracy or causal influence. The analysis is preliminary "
        "and should not be presented as a definitive global "
        "importance estimate for the complete dataset.\n"
    )

print("\n" + "=" * 70)
print("STEP 10G COMPLETED")
print("=" * 70)

print("\nOverall feature importance:")
print(importance_df.to_string(index=False))

print("\nSaved files:")
print(feature_plot)
print(heatmap_path)
print(class_plot)
print(importance_path)
print(class_csv)
print(report_path)

print("\nDisease-class-wise results:")
display(class_importance_df)