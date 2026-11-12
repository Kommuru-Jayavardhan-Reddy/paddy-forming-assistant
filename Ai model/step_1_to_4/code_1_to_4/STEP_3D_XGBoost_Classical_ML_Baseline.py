# ============================================================
# STEP 3D: XGBoost Classical ML Baseline
# ============================================================

!pip install -q xgboost

import xgboost as xgb
import numpy as np
import pandas as pd
import time
import json

from pathlib import Path
from datetime import datetime

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix
)

import matplotlib.pyplot as plt


# ============================================================
# 1. PROJECT DIRECTORIES
# ============================================================

PROJECT_ROOT = Path("/content/drive/MyDrive/final year project")

CODE_DIR = PROJECT_ROOT / "code"
RESULTS_DIR = PROJECT_ROOT / "results"
MODEL_DIR = PROJECT_ROOT / "models" / "ml"

CODE_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. LABELS -> INTEGER
#    Use VALID PATHS from STEP 3C
#    This prevents feature/label misalignment.
# ============================================================

def labels_from_paths(valid_paths, class_to_idx):
    labels = []

    for path in valid_paths:
        class_name = Path(path).parent.name

        if class_name not in class_to_idx:
            raise ValueError(
                f"Class '{class_name}' not found in class_to_idx."
            )

        labels.append(class_to_idx[class_name])

    return np.array(labels, dtype=np.int32)


y_train_ml = labels_from_paths(
    train_valid_paths,
    class_to_idx
)

y_val_ml = labels_from_paths(
    val_valid_paths,
    class_to_idx
)

y_test_ml = labels_from_paths(
    test_valid_paths,
    class_to_idx
)


# ============================================================
# 3. BASIC SAFETY CHECKS
# ============================================================

if len(X_train_ml) != len(y_train_ml):
    raise ValueError(
        f"Train mismatch: {len(X_train_ml)} features vs "
        f"{len(y_train_ml)} labels"
    )

if len(X_val_ml) != len(y_val_ml):
    raise ValueError(
        f"Validation mismatch: {len(X_val_ml)} features vs "
        f"{len(y_val_ml)} labels"
    )

if len(X_test_ml) != len(y_test_ml):
    raise ValueError(
        f"Test mismatch: {len(X_test_ml)} features vs "
        f"{len(y_test_ml)} labels"
    )


# ============================================================
# 4. DISPLAY DATA INFORMATION
# ============================================================

print("=" * 60)
print("STEP 3D: XGBOOST BASELINE")
print("=" * 60)

print("Train shape :", X_train_ml.shape)
print("Val shape   :", X_val_ml.shape)
print("Test shape  :", X_test_ml.shape)
print("Classes     :", len(classes))
print("Feature dim :", X_train_ml.shape[1])

print("\nLabel shapes:")
print("Train labels:", y_train_ml.shape)
print("Val labels  :", y_val_ml.shape)
print("Test labels :", y_test_ml.shape)


# ============================================================
# 5. MODEL
# ============================================================

xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,

    objective="multi:softprob",
    num_class=len(classes),

    eval_metric="mlogloss",

    subsample=0.8,
    colsample_bytree=0.8,

    tree_method="hist",

    random_state=42,
    n_jobs=-1
)


# ============================================================
# 6. TRAIN
# ============================================================

print("\nStarting XGBoost training...")

start = time.time()

xgb_model.fit(
    X_train_ml,
    y_train_ml,
    eval_set=[(X_train_ml, y_train_ml), (X_val_ml, y_val_ml)],
    verbose=False
)

training_time = time.time() - start

print(f"Training completed in {training_time:.2f} seconds.")


# ============================================================
# 7. VALIDATION
# ============================================================

val_pred = xgb_model.predict(X_val_ml)

val_accuracy = accuracy_score(
    y_val_ml,
    val_pred
)

val_macro_f1 = f1_score(
    y_val_ml,
    val_pred,
    average="macro"
)


# ============================================================
# 8. TEST
# ============================================================

test_pred = xgb_model.predict(X_test_ml)

test_accuracy = accuracy_score(
    y_test_ml,
    test_pred
)

test_macro_f1 = f1_score(
    y_test_ml,
    test_pred,
    average="macro"
)


# ============================================================
# 9. CLASSIFICATION REPORT
# ============================================================

test_report = classification_report(
    y_test_ml,
    test_pred,
    target_names=classes,
    digits=4
)


# ============================================================
# 10. RESULTS
# ============================================================

print("\n" + "=" * 60)
print("XGBOOST RESULTS")
print("=" * 60)

print(f"Training Time       : {training_time:.2f} sec")

print("\nVALIDATION")
print(f"Accuracy            : {val_accuracy:.4f}")
print(f"Macro F1            : {val_macro_f1:.4f}")

print("\nTEST")
print(f"Accuracy            : {test_accuracy:.4f}")
print(f"Macro F1            : {test_macro_f1:.4f}")

print("\nTEST CLASSIFICATION REPORT")
print(test_report)

print("=" * 60)


# ============================================================
# 11. SAVE ACTUAL XGBOOST MODEL
# ============================================================

model_path = MODEL_DIR / "xgboost_v1.json"

if model_path.exists():
    raise FileExistsError(
        f"\nModel already exists:\n{model_path}\n"
        "Training was NOT overwritten. "
        "Use a new version such as xgboost_v2.json if a new run is intended."
    )

xgb_model.save_model(str(model_path))


# ============================================================
# 12. SAVE METRICS CSV
# ============================================================

metrics_df = pd.DataFrame({
    "model": ["XGBoost"],
    "validation_accuracy": [val_accuracy],
    "validation_macro_f1": [val_macro_f1],
    "test_accuracy": [test_accuracy],
    "test_macro_f1": [test_macro_f1],
    "training_time_seconds": [training_time],
    "feature_dimension": [X_train_ml.shape[1]],
    "num_classes": [len(classes)],
    "n_estimators": [200],
    "max_depth": [6],
    "learning_rate": [0.1]
})

metrics_path = RESULTS_DIR / "STEP_3D_XGBoost_metrics.csv"

metrics_df.to_csv(
    metrics_path,
    index=False
)


# ============================================================
# 13. SAVE CLASSIFICATION REPORT
# ============================================================

report_path = RESULTS_DIR / "STEP_3D_XGBoost_classification_report.txt"

report_text = f"""
============================================================
STEP 3D: XGBOOST CLASSICAL ML BASELINE
============================================================

Execution Time:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Model:
XGBoost

Feature Dimension:
{X_train_ml.shape[1]}

Number of Classes:
{len(classes)}

Classes:
{classes}

Training Configuration
----------------------
n_estimators = 200
max_depth = 6
learning_rate = 0.1
subsample = 0.8
colsample_bytree = 0.8
tree_method = hist
random_state = 42
n_jobs = -1
objective = multi:softprob
eval_metric = mlogloss

Dataset Shapes
---------------
Train      : {X_train_ml.shape}
Validation : {X_val_ml.shape}
Test       : {X_test_ml.shape}

Training Time:
{training_time:.2f} seconds

Validation Accuracy:
{val_accuracy:.4f}

Validation Macro F1:
{val_macro_f1:.4f}

Test Accuracy:
{test_accuracy:.4f}

Test Macro F1:
{test_macro_f1:.4f}

============================================================
TEST CLASSIFICATION REPORT
============================================================

{test_report}

============================================================
ACTUAL TRAINED MODEL
============================================================

Saved:
YES

Model Path:
{model_path}

============================================================
"""

report_path.write_text(
    report_text,
    encoding="utf-8"
)


# ============================================================
# 14. SAVE CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_test_ml,
    test_pred
)

plt.figure(figsize=(12, 10))

plt.imshow(cm)

plt.title("XGBoost Test Confusion Matrix")
plt.xlabel("Predicted Class")
plt.ylabel("True Class")

plt.xticks(
    range(len(classes)),
    classes,
    rotation=90
)

plt.yticks(
    range(len(classes)),
    classes
)

plt.colorbar()

plt.tight_layout()

cm_path = RESULTS_DIR / "STEP_3D_XGBoost_confusion_matrix.png"

plt.savefig(
    cm_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ============================================================
# 15. SAVE XGBOOST EVALUATION HISTORY
# ============================================================

evals_result = xgb_model.evals_result()

history_rows = []

if "validation_0" in evals_result:
    for epoch, loss in enumerate(
        evals_result["validation_0"]["mlogloss"]
    ):
        history_rows.append({
            "epoch": epoch + 1,
            "dataset": "train",
            "mlogloss": loss
        })

if "validation_1" in evals_result:
    for epoch, loss in enumerate(
        evals_result["validation_1"]["mlogloss"]
    ):
        history_rows.append({
            "epoch": epoch + 1,
            "dataset": "validation",
            "mlogloss": loss
        })

history_df = pd.DataFrame(history_rows)

history_path = RESULTS_DIR / "STEP_3D_XGBoost_training_history.csv"

history_df.to_csv(
    history_path,
    index=False
)


# ============================================================
# 16. SAVE CLASS MAPPING
# ============================================================

mapping_path = RESULTS_DIR / "STEP_3D_XGBoost_class_mapping.json"

with open(mapping_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "class_to_idx": class_to_idx,
            "idx_to_class": {
                str(v): k
                for k, v in class_to_idx.items()
            },
            "classes": list(classes)
        },
        f,
        indent=4
    )


# ============================================================
# 17. SAVE MODEL METADATA
# ============================================================

metadata = {
    "model_name": "XGBoost",
    "model_version": "v1",
    "model_file": str(model_path),

    "classes": list(classes),
    "num_classes": len(classes),

    "input_size": "64x64",
    "feature_dimension": int(X_train_ml.shape[1]),

    "features": [
        "HSV histogram",
        "LBP texture",
        "HOG shape/edge"
    ],

    "preprocessing": {
        "resize": "64x64",
        "color_conversion": "BGR -> RGB",
        "hsv_histogram_bins": 64,
        "lbp_points": 24,
        "lbp_radius": 3,
        "hog_orientations": 9,
        "hog_pixels_per_cell": [8, 8],
        "hog_cells_per_block": [2, 2],
        "hog_block_norm": "L2-Hys"
    },

    "training": {
        "epochs_or_estimators": 200,
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "tree_method": "hist",
        "random_state": 42,
        "n_jobs": -1
    },

    "validation_accuracy": float(val_accuracy),
    "validation_macro_f1": float(val_macro_f1),

    "test_accuracy": float(test_accuracy),
    "test_macro_f1": float(test_macro_f1),

    "training_time_seconds": float(training_time),

    "created_at": datetime.now().isoformat()
}

metadata_path = RESULTS_DIR / "STEP_3D_XGBoost_metadata.json"

with open(metadata_path, "w", encoding="utf-8") as f:
    json.dump(
        metadata,
        f,
        indent=4
    )


# ============================================================
# 18. SAVE EXACT EXECUTED CODE
# ============================================================

try:
    executed_code = get_ipython().history_manager.input_hist_raw[-1]

    code_path = CODE_DIR / "STEP_3D_XGBoost_Classical_ML_Baseline.py"

    if not code_path.exists():
        code_path.write_text(
            executed_code,
            encoding="utf-8"
        )
        code_saved_status = "Created"
    else:
        code_saved_status = "Already exists - not overwritten"

except Exception as e:
    code_path = CODE_DIR / "STEP_3D_XGBoost_Classical_ML_Baseline.py"
    code_saved_status = f"Could not automatically save exact cell: {e}"


# ============================================================
# 19. FINAL STATUS
# ============================================================

print("\n" + "=" * 60)
print("STEP 3D COMPLETED")
print("=" * 60)

print("\nActual XGBoost model saved: YES")

print("\nMODEL:")
print(model_path)

print("\nMETRICS:")
print(metrics_path)

print("\nCLASSIFICATION REPORT:")
print(report_path)

print("\nCONFUSION MATRIX:")
print(cm_path)

print("\nTRAINING HISTORY:")
print(history_path)

print("\nCLASS MAPPING:")
print(mapping_path)

print("\nMODEL METADATA:")
print(metadata_path)

print("\nCODE BACKUP:")
print(code_path)

print("\nCode backup status:")
print(code_saved_status)

print("=" * 60)