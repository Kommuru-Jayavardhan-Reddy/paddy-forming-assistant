# ============================================================
# STEP_8A.2_BATCH GRAD-CAM FOR ALL TEST IMAGES
# ============================================================
import os
import csv
import time
import cv2
import torch
import numpy as np
import pandas as pd
from PIL import Image
from torchvision import transforms
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image


# ============================================================
# CONFIGURATION
# ============================================================

TEST_DIR = (
    "/content/drive/MyDrive/final year project/"
    "Dataset_Split/test"
)

OUTPUT_DIR = (
    "/content/drive/MyDrive/final year project/"
    "results/step8A_gradcam"
)

CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "step8A_gradcam_predictions.csv"
)

FAILED_CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "step8A_gradcam_failed_images.csv"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# CLASS LIST
# ============================================================

classes = [
    "bacterial_leaf_blight",
    "bacterial_leaf_streak",
    "bacterial_panicle_blight",
    "blast",
    "brown_spot",
    "dead_heart",
    "downy_mildew",
    "hispa",
    "leaf_scald",
    "leaf_smut",
    "normal",
    "sheath_blight",
    "tungro"
]


# ============================================================
# IMAGE TRANSFORM
# ============================================================

transform = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ============================================================
# COLLECT ALL TEST IMAGES
# ============================================================

print("=" * 90)
print("STEP 8A — PHASE 3: BATCH GRAD-CAM")
print("=" * 90)

print("\n[1] COLLECTING TEST IMAGES")
print("-" * 90)

image_records = []

valid_extensions = (
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
)

for class_name in classes:

    class_dir = os.path.join(
        TEST_DIR,
        class_name
    )

    if not os.path.isdir(class_dir):
        print(
            f"Directory not found: {class_name}"
        )
        continue

    files = sorted(os.listdir(class_dir))

    for filename in files:

        if filename.lower().endswith(valid_extensions):

            image_records.append({
                "image_path": os.path.join(
                    class_dir,
                    filename
                ),
                "ground_truth": class_name
            })


print("Total images found:", len(image_records))


# ============================================================
# EXPECTED DATASET SIZE
# ============================================================

EXPECTED_IMAGES = 3057

if len(image_records) != EXPECTED_IMAGES:

    print(
        f"\nDataset count differs from expected "
        f"{EXPECTED_IMAGES}."
    )

    print(
        "Actual count:",
        len(image_records)
    )

    print(
        "The code will continue using the images actually found."
    )

else:

    print(
        f"Dataset count verified: {EXPECTED_IMAGES}"
    )


# ============================================================
# MODEL CHECK
# ============================================================

print("\n[2] MODEL CHECK")
print("-" * 90)

model = model.to(device)
model.eval()

print("Device:", device)

if torch.cuda.is_available():
    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )

print(
    "Target layer:",
    model.features[-1]
)


# ============================================================
# GRAD-CAM OBJECT
# ============================================================

print("\n[3] INITIALIZING GRAD-CAM")
print("-" * 90)

target_layers = [
    model.features[-1]
]

cam = GradCAM(
    model=model,
    target_layers=target_layers
)

print("Grad-CAM initialized successfully.")


# ============================================================
# OUTPUT STRUCTURE
# ============================================================

print("\n[4] CREATING OUTPUT DIRECTORIES")
print("-" * 90)

for class_name in classes:

    class_output_dir = os.path.join(
        OUTPUT_DIR,
        class_name
    )

    os.makedirs(
        class_output_dir,
        exist_ok=True
    )

print("Class-wise output directories ready.")


# ============================================================
# BATCH PROCESSING
# ============================================================

results = []
failed = []

total = len(image_records)

start_time = time.time()

print("\n[5] STARTING BATCH GRAD-CAM")
print("-" * 90)

print("Total images:", total)
print()


for index, record in enumerate(
    image_records,
    start=1
):

    image_path = record["image_path"]
    ground_truth = record["ground_truth"]

    try:

        # ----------------------------------------------------
        # LOAD IMAGE
        # ----------------------------------------------------

        original = Image.open(
            image_path
        ).convert("RGB")

        # ----------------------------------------------------
        # PREPARE IMAGE
        # ----------------------------------------------------

        resized = original.resize(
            (380, 380)
        )

        rgb_image = (
            np.array(resized)
            .astype(np.float32)
            / 255.0
        )

        input_tensor = transform(
            original
        ).unsqueeze(0).to(device)

        # ----------------------------------------------------
        # PREDICTION
        # ----------------------------------------------------

        model.eval()

        with torch.no_grad():

            output = model(
                input_tensor
            )

            probabilities = torch.softmax(
                output,
                dim=1
            )

        predicted_index = (
            probabilities
            .argmax(dim=1)
            .item()
        )

        confidence = (
            probabilities[
                0,
                predicted_index
            ]
            .item()
        )

        predicted_class = classes[
            predicted_index
        ]

        # ----------------------------------------------------
        # GRAD-CAM
        # ----------------------------------------------------

        targets = [
            ClassifierOutputTarget(
                predicted_index
            )
        ]

        grayscale_cam = cam(
            input_tensor=input_tensor,
            targets=targets
        )[0]

        # ----------------------------------------------------
        # SANITY CHECK
        # ----------------------------------------------------

        if (
            grayscale_cam is None
            or grayscale_cam.size == 0
        ):
            raise RuntimeError(
                "Empty Grad-CAM output"
            )

        if not np.isfinite(
            grayscale_cam
        ).all():

            raise RuntimeError(
                "Grad-CAM contains NaN/Inf"
            )

        # ----------------------------------------------------
        # CREATE OVERLAY
        # ----------------------------------------------------

        visualization = show_cam_on_image(
            rgb_image,
            grayscale_cam,
            use_rgb=True
        )

        # ----------------------------------------------------
        # OUTPUT FILE
        # ----------------------------------------------------

        filename = os.path.basename(
            image_path
        )

        stem = os.path.splitext(
            filename
        )[0]

        class_output_dir = os.path.join(
            OUTPUT_DIR,
            ground_truth
        )

        output_filename = (
            f"{stem}_gradcam.png"
        )

        output_path = os.path.join(
            class_output_dir,
            output_filename
        )

        # ----------------------------------------------------
        # SAVE PNG
        # ----------------------------------------------------

        cv2.imwrite(
            output_path,
            cv2.cvtColor(
                visualization,
                cv2.COLOR_RGB2BGR
            )
        )

        # ----------------------------------------------------
        # SAVE RESULT
        # ----------------------------------------------------

        results.append({

            "image_path":
                image_path,

            "ground_truth":
                ground_truth,

            "predicted_class":
                predicted_class,

            "confidence":
                float(confidence),

            "gradcam_path":
                output_path
        })

        # ----------------------------------------------------
        # PROGRESS
        # ----------------------------------------------------

        if (
            index == 1
            or index % 50 == 0
            or index == total
        ):

            elapsed = (
                time.time()
                - start_time
            )

            rate = (
                index / elapsed
                if elapsed > 0
                else 0
            )

            remaining = (
                (total - index) / rate
                if rate > 0
                else 0
            )

            print(
                f"[{index:4d}/{total}] "
                f"{index / total * 100:6.2f}% | "
                f"GT={ground_truth:28s} | "
                f"Pred={predicted_class:28s} | "
                f"Conf={confidence * 100:6.2f}% | "
                f"ETA={remaining / 60:6.1f} min"
            )

    except Exception as e:

        failed.append({

            "image_path":
                image_path,

            "ground_truth":
                ground_truth,

            "error":
                str(e)
        })

        print(
            f"[FAILED {index}/{total}] "
            f"{os.path.basename(image_path)}"
        )

        print(
            "   Error:",
            str(e)
        )


# ============================================================
# SAVE MAIN CSV
# ============================================================

print("\n[6] SAVING RESULTS")
print("-" * 90)

results_df = pd.DataFrame(
    results
)

results_df.to_csv(
    CSV_PATH,
    index=False
)

print(
    "Prediction CSV saved:"
)

print(CSV_PATH)


# ============================================================
# SAVE FAILED CSV
# ============================================================

failed_df = pd.DataFrame(
    failed
)

failed_df.to_csv(
    FAILED_CSV_PATH,
    index=False
)

print(
    "Failed-image CSV saved:"
)

print(FAILED_CSV_PATH)


# ============================================================
# FINAL STATISTICS
# ============================================================

elapsed_total = (
    time.time()
    - start_time
)

successful = len(results)
failed_count = len(failed)

print("\n[7] FINAL STATISTICS")
print("-" * 90)

print(
    "Total images      :",
    total
)

print(
    "Successfully done :",
    successful
)

print(
    "Failed images     :",
    failed_count
)

print(
    "Success percentage:",
    f"{successful / total * 100:.2f}%"
    if total > 0
    else "0%"
)

print(
    "Total time        :",
    f"{elapsed_total / 60:.2f} minutes"
)


# ============================================================
# PREDICTION ACCURACY CHECK
# ============================================================

if successful > 0:

    correct = (
        results_df["ground_truth"]
        ==
        results_df["predicted_class"]
    ).sum()

    accuracy = (
        correct / successful
    )

    print("\n[8] BATCH PREDICTION CHECK")
    print("-" * 90)

    print(
        "Correct predictions:",
        correct
    )

    print(
        "Incorrect predictions:",
        successful - correct
    )

    print(
        "Accuracy on processed images:",
        f"{accuracy * 100:.2f}%"
    )


# ============================================================
# GRAD-CAM OUTPUT CHECK
# ============================================================

if successful > 0:

    existing_outputs = (
        results_df["gradcam_path"]
        .apply(os.path.exists)
        .sum()
    )

else:

    existing_outputs = 0


print("\n[9] OUTPUT FILE VERIFICATION")
print("-" * 90)

print(
    "Expected successful outputs:",
    successful
)

print(
    "Existing PNG outputs:",
    existing_outputs
)

print(
    "Missing PNG outputs:",
    successful - existing_outputs
)


# ============================================================
# CLASS-WISE SUMMARY
# ============================================================

if successful > 0:

    print("\n[10] CLASS-WISE SUMMARY")
    print("-" * 90)

    summary = (
        results_df
        .groupby("ground_truth")
        .agg(
            samples=("image_path", "count"),
            correct=(
                "predicted_class",
                lambda x: (
                    x
                    ==
                    results_df.loc[
                        x.index,
                        "ground_truth"
                    ]
                ).sum()
            ),
            mean_confidence=(
                "confidence",
                "mean"
            )
        )
        .reset_index()
    )

    summary["accuracy"] = (
        summary["correct"]
        /
        summary["samples"]
    )

    for _, row in summary.iterrows():

        print(
            f"{row['ground_truth']:30s} | "
            f"Samples={int(row['samples']):4d} | "
            f"Correct={int(row['correct']):4d} | "
            f"Accuracy={row['accuracy'] * 100:6.2f}% | "
            f"Mean Conf={row['mean_confidence'] * 100:6.2f}%"
        )


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 90)
print("STEP 8A — PHASE 3 COMPLETE")
print("=" * 90)

if (
    successful == total
    and existing_outputs == total
    and failed_count == 0
):

    print("All test images processed successfully.")
    print("All Grad-CAM PNG outputs verified.")
    print("Failed images: 0")
    print("STEP 8A BATCH GRAD-CAM: COMPLETE")

else:

    print(
        "Batch processing completed with some images "
        "requiring review."
    )

    print(
        "Successful:",
        successful
    )

    print(
        "Failed:",
        failed_count
    )

print("\nMain CSV:")
print(CSV_PATH)

print("\nFailed CSV:")
print(FAILED_CSV_PATH)

print("=" * 90)