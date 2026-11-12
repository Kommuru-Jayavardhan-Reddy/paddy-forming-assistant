"""
Paddy Farming Assistant - Multimodal Prediction Service (STEP 11D.3)
Orchestrates multimodal disease classification by extracting visual embeddings
via the trained EfficientNet-B4 image branch, retrieving field satellite sequences,
and executing the trained TemporalCrossAttentionModel on CPU.
"""

import io
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

import torch
import torchvision.transforms as transforms

from app import config
from app.exceptions import (
    FieldNotFoundError,
    SatelliteDataUnavailableError,
    ModelUnavailableError,
    ModelInferenceError,
)
from app.models.model_loader import ModelLoader
from app.models.multimodal_model import MultimodalModelLoader, TemporalCrossAttentionModel
from app.services.field_mapping import FieldMappingService

logger = logging.getLogger(__name__)


class MultimodalPredictionService:
    """
    Executes cross-attention multimodal paddy disease classification.
    Strictly combines:
    1. 1792-D visual feature embedding from EfficientNet-B4 backbone.
    2. (10, 3) Sentinel-2 temporal NDVI/NDRE/GNDVI sequence from FieldMappingService.
    3. TemporalCrossAttentionModel for classification over 11 verified classes.
    """

    def __init__(self):
        self.device = config.DEVICE
        self.field_service = FieldMappingService.get_instance()

        # Visual transforms matching Step 7D embedding generation:
        # Resize(380, 380) -> ToTensor() -> ImageNet Normalization
        self.image_transform = transforms.Compose([
            transforms.Resize((config.MULTIMODAL_IMAGE_SIZE, config.MULTIMODAL_IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=config.IMAGENET_MEAN,
                std=config.IMAGENET_STD,
            ),
        ])

    def load_image(self, image_input: Union[bytes, io.BytesIO, Path, str, Image.Image]) -> Image.Image:
        """
        Safely decodes image bytes, handles phone EXIF orientation, and converts to RGB.
        """
        try:
            if isinstance(image_input, Image.Image):
                image = image_input
            elif isinstance(image_input, (str, Path)):
                image = Image.open(image_input)
            elif isinstance(image_input, bytes):
                image = Image.open(io.BytesIO(image_input))
            elif hasattr(image_input, "read"):
                image = Image.open(image_input)
            else:
                raise ValueError(f"Unsupported image input type: {type(image_input)}")

            image = ImageOps.exif_transpose(image)
            if image.mode != "RGB":
                image = image.convert("RGB")
            return image
        except (UnidentifiedImageError, OSError, ValueError) as err:
            logger.error("Failed to decode image for multimodal inference: %s", err)
            raise ValueError(f"Invalid or corrupted image file: {err}") from err

    def preprocess_image(self, image_input: Union[bytes, io.BytesIO, Path, str, Image.Image]) -> torch.Tensor:
        """
        Preprocesses image into normalized tensor [3, 380, 380].
        """
        image = self.load_image(image_input)
        return self.image_transform(image)

    def extract_image_embedding(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """
        Extracts 1792-D visual feature vector using EfficientNet-B4 backbone (features + avgpool + Flatten).
        """
        eff_model = ModelLoader.get_model()
        if eff_model is None:
            raise ModelUnavailableError("EfficientNet-B4 image model is not available.")

        # Backbone extractor: features -> adaptive avgpool -> flatten
        feature_extractor = torch.nn.Sequential(
            eff_model.features,
            eff_model.avgpool,
            torch.nn.Flatten(),
        )
        feature_extractor.eval()

        with torch.inference_mode():
            embedding = feature_extractor(image_tensor.to(self.device))
        return embedding  # [B, 1792]

    def prepare_satellite_tensor(
        self, field_id: str, sat_mean: np.ndarray, sat_std: np.ndarray
    ) -> Tuple[torch.Tensor, str]:
        """
        Retrieves and normalizes the (10, 3) satellite sequence for field_id.
        Raises FieldNotFoundError (404) if field_id is unknown.
        Raises SatelliteDataUnavailableError (503) if sequence data is missing or corrupted.
        """
        field_info = self.field_service.get_field(field_id)
        if field_info is None:
            logger.warning("Multimodal field lookup failed for '%s'", field_id)
            raise FieldNotFoundError(f"Field '{field_id}' was not found in the master field catalog.")

        canonical_field_id = field_info["field_id"]
        raw_seq = self.field_service.get_satellite_sequence(canonical_field_id)

        if raw_seq is None:
            logger.error("Satellite sequence unavailable for field '%s'", canonical_field_id)
            raise SatelliteDataUnavailableError(
                f"Satellite time-series sequence data is unavailable for field '{canonical_field_id}'."
            )

        if raw_seq.shape != (config.SATELLITE_TIMESTEPS, config.NUM_SATELLITE_FEATURES):
            logger.error("Malformed sequence shape %s for field %s", raw_seq.shape, canonical_field_id)
            raise SatelliteDataUnavailableError(
                f"Satellite sequence has malformed dimensions {raw_seq.shape} (expected 10x3)."
            )

        if np.isnan(raw_seq).any() or np.isinf(raw_seq).any():
            logger.error("Satellite sequence for field %s contains NaN or Inf.", canonical_field_id)
            raise SatelliteDataUnavailableError(
                f"Satellite sequence for field '{canonical_field_id}' contains corrupt numerical values."
            )

        # Apply exact training-time normalization: (seq - mean) / std
        normalized_seq = (raw_seq - sat_mean) / sat_std
        sat_tensor = torch.from_numpy(normalized_seq).unsqueeze(0).to(self.device).float()
        return sat_tensor, canonical_field_id

    def predict(
        self,
        image_input: Union[bytes, io.BytesIO, Path, str, Image.Image],
        field_id: str,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Synchronous multimodal inference fusing real uploaded image and real field satellite time-series.
        """
        # 1. Load multimodal model and metadata
        try:
            multimodal_model = MultimodalModelLoader.get_model()
            metadata = MultimodalModelLoader.get_metadata()
        except FileNotFoundError as err:
            logger.error("Multimodal model checkpoint missing: %s", err)
            raise ModelUnavailableError("Multimodal cross-attention model checkpoint is unavailable.") from err
        except Exception as err:
            logger.error("Failed to load multimodal model: %s", err, exc_info=True)
            raise ModelUnavailableError(f"Failed to load multimodal model: {err}") from err

        class_names: List[str] = metadata["class_names"]
        num_classes: int = metadata["num_classes"]
        sat_mean: np.ndarray = metadata["satellite_mean"]
        sat_std: np.ndarray = metadata["satellite_std"]

        # 2. Retrieve and normalize satellite sequence for the field
        sat_tensor, canonical_field_id = self.prepare_satellite_tensor(field_id, sat_mean, sat_std)

        # 3. Preprocess image and extract 1792-D visual embedding
        image_tensor = self.preprocess_image(image_input).unsqueeze(0)  # [1, 3, 380, 380]
        image_embedding = self.extract_image_embedding(image_tensor)     # [1, 1792]

        # 4. Execute multimodal cross-attention model
        try:
            with torch.inference_mode():
                logits, attention = multimodal_model(image_embedding, sat_tensor)
                probabilities = torch.softmax(logits, dim=1)[0]  # [11]

            # 5. Extract top-k predictions
            k = min(top_k, num_classes)
            top_probs, top_indices = torch.topk(probabilities, k=k)

            top_probs_list = top_probs.cpu().tolist()
            top_indices_list = top_indices.cpu().tolist()

            predicted_idx = top_indices_list[0]
            predicted_class = class_names[predicted_idx]
            confidence = float(top_probs_list[0])

            top_predictions = [
                {
                    "disease": class_names[idx],
                    "probability": round(float(prob), 4),
                    "index": int(idx),
                }
                for idx, prob in zip(top_indices_list, top_probs_list)
            ]

            # Attention weights over 10 timesteps
            attention_weights = attention[0, 0].cpu().tolist()

            return {
                "prediction_mode": "multimodal",
                "field_id": canonical_field_id,
                "predicted_class": predicted_class,
                "confidence": round(confidence, 4),
                "top_3_predictions": top_predictions,
                "image_model_status": ModelLoader.get_model_status(),
                "satellite_model_status": "loaded",
                "fusion_model_status": MultimodalModelLoader.get_status(),
                "temporal_attention_weights": [round(w, 4) for w in attention_weights],
                "satellite_timesteps": config.SATELLITE_TIMESTEPS,
                "device": self.device,
                "note": (
                    "Multimodal prediction fuses leaf visual features with field satellite time-series for advisory guidance. "
                    "Satellite features provide field environmental context; visual features dominate leaf lesion morphology."
                ),
            }

        except Exception as err:
            logger.error("Multimodal inference execution error: %s", err, exc_info=True)
            raise ModelInferenceError(f"Multimodal inference failed: {err}") from err
