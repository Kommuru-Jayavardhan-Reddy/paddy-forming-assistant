"""
Paddy Farming Assistant - Backend Configuration
Centralizes application settings, CORS, hardware device configuration,
upload limits, and model artifact paths with environment variable support.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Base Directory Resolution
BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_PROJECT_DIR = BACKEND_DIR.parent

# Load local .env if present in backend directory
ENV_FILE = BACKEND_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()

# Application Information
PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Paddy Farming Assistant API")
API_VERSION: str = os.getenv("API_VERSION", "v1")
PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "1.0.0")
MODEL_VERSION: str = os.getenv("MODEL_VERSION", "phaseC_best")
MULTIMODAL_MODEL_VERSION: str = os.getenv("MULTIMODAL_MODEL_VERSION", "step7L_controlled_best")
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Server Configuration
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", 8000))

def _parse_cors_origins(raw: str) -> List[str]:
    """
    Parses comma-separated CORS origins, removing whitespace,
    trailing slashes, and duplicate entries while preserving order.
    """
    origins: List[str] = []
    seen = set()
    for item in raw.split(","):
        cleaned = item.strip().rstrip("/")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            origins.append(cleaned)
    return origins


# CORS Configuration
# Allows requests from Vite frontend development server
raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173,null")
CORS_ORIGINS: List[str] = _parse_cors_origins(raw_cors)

# Security constraint: Do not enable credentials if wildcard origin is configured
CORS_ALLOW_CREDENTIALS: bool = "*" not in CORS_ORIGINS

# File Upload Constraints
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

# Hardware & Inference Configuration
# Laptop constraint: defaults to CPU inference
DEVICE: str = os.getenv("DEVICE", "cpu").lower()


def _resolve_path(env_var_name: str, default_path: Path) -> Path:
    """
    Resolves relative or absolute path from environment variable,
    falling back to standard project structure default.
    """
    configured_val = os.getenv(env_var_name)
    if not configured_val:
        return default_path
    
    path = Path(configured_val)
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    return path


# Model Artifact Locations (Preserving existing checkpoints in AI_model)
EFFICIENTNET_CHECKPOINT_PATH: Path = _resolve_path(
    "EFFICIENTNET_CHECKPOINT_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_1_to_4" / "models" / "dl" / "efficientnet_b4_phaseC_best.pth",
)

MODEL_METADATA_PATH: Path = _resolve_path(
    "MODEL_METADATA_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_1_to_4" / "STEP_4A_EfficientNet_B4_metadata.json",
)

MULTIMODAL_CHECKPOINT_PATH: Path = _resolve_path(
    "MULTIMODAL_CHECKPOINT_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 7" / "models_7" / "Step7L_Temporal_CrossAttention_m_1" / "step7L_controlled_best.pth",
)

# Satellite Data & Field Mapping Artifacts (Step 5 - 10)
SATELLITE_SEQUENCES_PATH: Path = _resolve_path(
    "SATELLITE_SEQUENCES_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 5" / "models_5" / "bilstm_sequences.npy",
)

FIELD_MASTER_MAPPING_PATH: Path = _resolve_path(
    "FIELD_MASTER_MAPPING_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 7" / "step7_verified_field_embedding_mapping.csv",
)

FIELD_LOCATIONS_PATH: Path = _resolve_path(
    "FIELD_LOCATIONS_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 5" / "text_and_csv_files_5" / "field_locations.csv",
)

MULTIMODAL_DATASET_MAPPING_PATH: Path = _resolve_path(
    "MULTIMODAL_DATASET_MAPPING_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 7" / "text_and_csv_files_7" / "step7I_final_11class_multimodal_dataset.csv",
)

FIELD_EMBEDDINGS_PATH: Path = _resolve_path(
    "FIELD_EMBEDDINGS_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 6" / "models_6" / "step6F_final_satellite_embeddings.npy",
)

PAIRED_SATELLITE_EMBEDDINGS_PATH: Path = _resolve_path(
    "PAIRED_SATELLITE_EMBEDDINGS_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 7" / "models_7" / "step7E_paired_satellite_embeddings_640x256.npy",
)

SENTINEL2_TIMESERIES_CSV_PATH: Path = _resolve_path(
    "SENTINEL2_TIMESERIES_CSV_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 5" / "code_5" / "sentinel2_timeseries.csv",
)


# Satellite Data Specifications (Step 5 & 6)
SATELLITE_TIMESTEPS: int = 10
SATELLITE_FEATURES: List[str] = ["NDVI", "NDRE", "GNDVI"]
NUM_SATELLITE_FEATURES: int = len(SATELLITE_FEATURES)
TOTAL_SATELLITE_FIELDS: int = 58

# EfficientNet-B4 Preprocessing Specifications (from Step 2B & Step 4A)
IMAGE_SIZE: int = 224
IMAGENET_MEAN: List[float] = [0.485, 0.456, 0.406]
IMAGENET_STD: List[float] = [0.229, 0.224, 0.225]

# Verified 13 Disease Classes (from STEP_4A metadata)
DISEASE_CLASSES: List[str] = [
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
    "tungro",
]
NUM_CLASSES: int = len(DISEASE_CLASSES)

# Multimodal Cross-Attention Model Specifications (Step 7L & Step 9)
MULTIMODAL_IMAGE_SIZE: int = 380
MULTIMODAL_CLASSES: List[str] = [
    "bacterial_leaf_blight",
    "bacterial_leaf_streak",
    "bacterial_panicle_blight",
    "blast",
    "brown_spot",
    "dead_heart",
    "downy_mildew",
    "hispa",
    "leaf_scald",
    "sheath_blight",
    "tungro",
]
NUM_MULTIMODAL_CLASSES: int = len(MULTIMODAL_CLASSES)

# Grad-CAM Visualization Paths (Step 11D.5)
STATIC_DIR: Path = BACKEND_DIR / "static"
GRADCAM_OUTPUT_DIR: Path = STATIC_DIR / "visualizations" / "gradcam"
GRADCAM_TARGET_LAYER: str = "features.8"

# SHAP Explainability Paths & Parameters (Step 11D.6)
SHAP_BACKGROUND_PATH: Path = _resolve_path(
    "SHAP_BACKGROUND_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 10" / "models_10" / "shap_satellite_background.npy",
)
SHAP_BACKGROUND_INDICES_PATH: Path = _resolve_path(
    "SHAP_BACKGROUND_INDICES_PATH",
    BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 10" / "models_10" / "shap_background_indices.npy",
)
SHAP_OUTPUT_DIR: Path = STATIC_DIR / "visualizations" / "shap"
SHAP_NSAMPLES: int = int(os.getenv("SHAP_NSAMPLES", "100"))

# Ensure static and visualization output directories exist
GRADCAM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SHAP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Report Document Storage Paths (Step 11I.4)
REPORTS_STORAGE_DIR: Path = BACKEND_DIR / "reports_storage"
REPORTS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Weather Service Configuration (Step 11E - Open-Meteo)
WEATHER_PROVIDER: str = os.getenv("WEATHER_PROVIDER", "Open-Meteo")
WEATHER_API_BASE_URL: str = os.getenv("WEATHER_API_BASE_URL", "https://api.open-meteo.com/v1/forecast")
WEATHER_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("WEATHER_REQUEST_TIMEOUT_SECONDS", "10.0"))
WEATHER_SERVICE_ENABLED: bool = os.getenv("WEATHER_SERVICE_ENABLED", "True").lower() in ("true", "1", "yes")
WEATHER_DEFAULT_TIMEZONE: str = os.getenv("WEATHER_DEFAULT_TIMEZONE", "Asia/Kolkata")

# Database Configuration (STEP 11F - PostgreSQL & SQLAlchemy)
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "paddy_farming_db")
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "paddy_app")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")

DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "True").lower() in ("true", "1", "yes")
DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() in ("true", "1", "yes")

# Market Price Service Configuration (Step 11G - Data.gov.in / Agmarknet)
MARKET_SERVICE_ENABLED: bool = os.getenv("MARKET_SERVICE_ENABLED", "True").lower() in ("true", "1", "yes")
MARKET_PROVIDER: str = os.getenv("MARKET_PROVIDER", "Data.gov.in")
DATAGOVIN_API_KEY: Optional[str] = os.getenv("DATAGOVIN_API_KEY", None)
DATAGOVIN_RESOURCE_ID: str = os.getenv("DATAGOVIN_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")
DATAGOVIN_BASE_URL: str = os.getenv(
    "DATAGOVIN_BASE_URL",
    f"https://api.data.gov.in/resource/{DATAGOVIN_RESOURCE_ID}",
)
MARKET_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("MARKET_REQUEST_TIMEOUT_SECONDS", "15.0"))
MARKET_CACHE_TTL_MINUTES: int = int(os.getenv("MARKET_CACHE_TTL_MINUTES", "720"))
MARKET_STALENESS_DAYS: int = int(os.getenv("MARKET_STALENESS_DAYS", "3"))
MARKET_SYNC_COOLDOWN_MINUTES: int = int(os.getenv("MARKET_SYNC_COOLDOWN_MINUTES", "15"))




# Security & JWT Authentication Configuration (Step 1 & 1A - Argon2id & PyJWT)
ALLOWED_JWT_ALGORITHMS: List[str] = ["HS256"]
_configured_jwt_alg: str = os.getenv("JWT_ALGORITHM", "HS256").strip().upper()
if _configured_jwt_alg not in ALLOWED_JWT_ALGORITHMS:
    raise ValueError(
        f"Unsupported or unapproved JWT algorithm '{_configured_jwt_alg}'. "
        f"Strictly allowed algorithms: {ALLOWED_JWT_ALGORITHMS}"
    )
JWT_ALGORITHM: str = _configured_jwt_alg
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

