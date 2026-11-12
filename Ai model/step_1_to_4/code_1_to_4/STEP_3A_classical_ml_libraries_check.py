# STEP 3A: Classical ML Libraries Check

import cv2
import numpy as np
import pandas as pd

from skimage.feature import local_binary_pattern, hog
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score

print("=" * 60)
print("CLASSICAL ML LIBRARIES")
print("=" * 60)

print("OpenCV        :", cv2.__version__)
print("NumPy         :", np.__version__)
print("Pandas        :", pd.__version__)

print("\nAll required libraries imported successfully.")
print("=" * 60)
