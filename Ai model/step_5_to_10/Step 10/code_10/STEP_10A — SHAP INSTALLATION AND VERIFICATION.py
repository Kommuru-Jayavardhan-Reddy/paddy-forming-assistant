# ============================================================
# STEP_10A — SHAP INSTALLATION AND VERIFICATION
# ============================================================

import sys
import subprocess
import importlib.util

print("=" * 65)
print("STEP_10A — SHAP SETUP")
print("=" * 65)

# Check whether SHAP is already installed
if importlib.util.find_spec("shap") is None:
    print("\nSHAP is not installed. Installing SHAP...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "shap"
    ])
else:
    print("\nSHAP is already installed.")

# Import and verify
import shap
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

print("\nSHAP version:", shap.__version__)
print("PyTorch version:", torch.__version__)
print("NumPy version:", np.__version__)
print("Pandas version:", pd.__version__)

print("\nRequired libraries imported successfully.")
print("STEP_10A COMPLETED")