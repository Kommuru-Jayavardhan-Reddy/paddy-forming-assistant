# ============================================================
# STEP 2A: CHECK PYTORCH ENVIRONMENT
# ============================================================

import torch
import torchvision

print("=" * 60)
print("PYTORCH ENVIRONMENT")
print("=" * 60)

print("PyTorch version     :", torch.__version__)
print("Torchvision version :", torchvision.__version__)
print("CUDA available      :", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU                 :", torch.cuda.get_device_name(0))
    print("CUDA version        :", torch.version.cuda)
else:
    print("GPU                 : Not available")
    print("CUDA version        : Not available")

print("=" * 60)

# Save environment information
from pathlib import Path

RESULTS_DIR = Path(
    "/content/drive/MyDrive/final year project/results"
)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

report_path = RESULTS_DIR / "Step_2A_PyTorch_Environment.txt"

with open(report_path, "w", encoding="utf-8") as f:
    f.write("STEP 2A: PYTORCH ENVIRONMENT\n")
    f.write("=" * 60 + "\n")
    f.write(f"PyTorch version     : {torch.__version__}\n")
    f.write(f"Torchvision version : {torchvision.__version__}\n")
    f.write(f"CUDA available      : {torch.cuda.is_available()}\n")

    if torch.cuda.is_available():
        f.write(f"GPU                 : {torch.cuda.get_device_name(0)}\n")
        f.write(f"CUDA version        : {torch.version.cuda}\n")
    else:
        f.write("GPU                 : Not available\n")
        f.write("CUDA version        : Not available\n")

    f.write("=" * 60 + "\n")

print("\n✅ Step 2A completed.")
print("📁 Report saved:", report_path)