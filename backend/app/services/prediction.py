"""
Paddy Farming Assistant - Prediction Service
Handles image preprocessing, model inference orchestration, and output post-processing.
Keeps inference logic separate from API routing and model definitions.
"""

import io
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from PIL import Image, ImageOps, UnidentifiedImageError

import torch
import torchvision.transforms as transforms

from app import config
from app.models.model_loader import ModelLoader

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.60


class PredictionService:
    """
    Orchestrates paddy disease prediction on leaf images.
    Reuses the trained EfficientNet-B4 PyTorch model on CPU.
    """

    def __init__(self):
        self.device = config.DEVICE
        self.classes: List[str] = config.DISEASE_CLASSES
        self.num_classes: int = config.NUM_CLASSES

        # Preprocessing matching training:
        # Resize(224, 224) -> ToTensor() -> ImageNet Normalization
        self.transform = transforms.Compose([
            transforms.Resize((config.IMAGE_SIZE, config.IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=config.IMAGENET_MEAN,
                std=config.IMAGENET_STD,
            ),
        ])

    def load_image(self, image_input: Union[bytes, io.BytesIO, Path, str, Image.Image]) -> Image.Image:
        """
        Safely opens input image data using Pillow.
        Fixes phone-photo rotation (EXIF) and converts everything to RGB.
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

            # Fix rotation stored in phone photo metadata
            image = ImageOps.exif_transpose(image)

            # Guarantee 3 channels
            if image.mode != "RGB":
                image = image.convert("RGB")

            return image
        except (UnidentifiedImageError, OSError, ValueError) as err:
            logger.error("Failed to decode image: %s", err)
            raise ValueError(f"Invalid or corrupted image file: {err}") from err

    def preprocess_image(self, image_input: Union[bytes, io.BytesIO, Path, str, Image.Image]) -> torch.Tensor:
        """
        Returns a tensor of shape [3, 224, 224], ImageNet-normalized.
        """
        image = self.load_image(image_input)
        return self.transform(image)

    def predict(
        self,
        image_input: Union[bytes, io.BytesIO, Path, str, Image.Image],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Runs EfficientNet-B4 inference and returns disease, confidence and top-k.
        """
        model = ModelLoader.get_model()
        if model is None:
            raise RuntimeError("ModelLoader failed to initialize EfficientNet-B4 model.")

        tensor = self.preprocess_image(image_input)
        batch_tensor = tensor.unsqueeze(0).to(self.device)  # [1, 3, 224, 224]

        with torch.inference_mode():
            logits = model(batch_tensor)
            probabilities = torch.softmax(logits, dim=1)[0]  # [num_classes]

        k = min(top_k, self.num_classes)
        top_probs, top_indices = torch.topk(probabilities, k=k)

        top_probs_list = top_probs.cpu().tolist()
        top_indices_list = top_indices.cpu().tolist()

        predicted_idx = top_indices_list[0]
        predicted_disease = self.classes[predicted_idx]
        confidence = float(top_probs_list[0])

        top_predictions = [
            {
                "disease": self.classes[idx],
                "probability": round(float(prob), 4),
                "index": int(idx),
            }
            for idx, prob in zip(top_indices_list, top_probs_list)
        ]

        return {
            "status": "success",
            "predicted_index": int(predicted_idx),
            "disease": predicted_disease,
            "confidence": round(confidence, 4),
            "is_healthy": predicted_disease == "normal",
            "low_confidence": confidence < LOW_CONFIDENCE_THRESHOLD,
            "top3": top_predictions,
            "device": self.device,
            "note": "Confidence score represents softmax probability distribution and serves as advisory guidance.",
        }

    async def predict_image(
        self,
        image_bytes: bytes,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        field_id: Optional[str] = None,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Asynchronous wrapper for FastAPI route integration.
        """
        result = self.predict(image_bytes, top_k=top_k)
        if field_id:
            result["field_id"] = field_id
        if latitude is not None and longitude is not None:
            result["coordinates"] = {"latitude": latitude, "longitude": longitude}
        return result