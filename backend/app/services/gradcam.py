"""
Paddy Farming Assistant - Grad-CAM Service (STEP 11D.5)
Implements Gradient-weighted Class Activation Mapping (Grad-CAM)
for the trained EfficientNet-B4 paddy disease classification model.
Visualizes salient receptive fields influencing disease class scores on CPU.
"""

import io
import base64
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
import numpy as np
from PIL import Image

import torch
import torch.nn.functional as F

from app import config
from app.exceptions import ModelUnavailableError, ModelInferenceError
from app.models.model_loader import ModelLoader
from app.services.prediction import PredictionService

logger = logging.getLogger(__name__)


class GradCAMService:
    """
    Computes class-specific Grad-CAM visual explanations on the final
    convolutional layer (features[8]) of EfficientNet-B4.
    """

    def __init__(self):
        self.device = config.DEVICE
        self.classes = config.DISEASE_CLASSES
        self.num_classes = config.NUM_CLASSES
        self.pred_service = PredictionService()
        self.target_layer_name = config.GRADCAM_TARGET_LAYER

        # Ensure output directory exists for safe storage
        config.GRADCAM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def apply_jet_colormap(heatmap: np.ndarray) -> np.ndarray:
        """
        Converts 2D float array in [0, 1] to standard RGB Jet heatmap uint8 array.
        Pure NumPy implementation with no OpenCV or Matplotlib dependencies.
        """
        r = np.clip(1.5 - np.abs(4.0 * heatmap - 3.0), 0.0, 1.0)
        g = np.clip(1.5 - np.abs(4.0 * heatmap - 2.0), 0.0, 1.0)
        b = np.clip(1.5 - np.abs(4.0 * heatmap - 1.0), 0.0, 1.0)
        rgb = np.stack([r, g, b], axis=-1)
        return (rgb * 255.0).astype(np.uint8)

    def validate_target_class(
        self, target_class: Optional[str] = None, target_index: Optional[int] = None
    ) -> Optional[int]:
        """
        Validates requested target class or index against the 13 supported disease classes.
        Returns the validated 0-indexed integer class index or None.
        """
        if target_index is not None:
            if not (0 <= target_index < self.num_classes):
                raise ValueError(
                    f"Invalid target_index {target_index}. Must be between 0 and {self.num_classes - 1}."
                )
            return target_index

        if target_class is not None:
            cleaned = target_class.strip().lower()
            if cleaned not in self.classes:
                raise ValueError(
                    f"Invalid target_class '{target_class}'. Must be one of: {', '.join(self.classes)}"
                )
            return self.classes.index(cleaned)

        return None

    def generate_gradcam(
        self,
        image_input: Union[bytes, io.BytesIO, Path, str, Image.Image],
        target_class: Optional[str] = None,
        target_index: Optional[int] = None,
        alpha: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Executes Grad-CAM on EfficientNet-B4 features[8] and blends heatmap over original image.
        Guarantees cleanup of hooks, leaves weights intact, and handles constant activations safely.
        """
        # 1. Load trained EfficientNet-B4 model
        model = ModelLoader.get_model()
        if model is None:
            raise ModelUnavailableError("EfficientNet-B4 model is currently unavailable.")
        model.eval()

        # 2. Decode and record original image dimensions
        orig_image = self.pred_service.load_image(image_input)
        orig_w, orig_h = orig_image.size

        # 3. Preprocess matching PredictionService (224x224, ImageNet normalized)
        input_tensor = self.pred_service.preprocess_image(orig_image).unsqueeze(0).to(self.device)
        input_tensor.requires_grad = True

        # 4. Target convolutional layer: model.features[8]
        target_layer = model.features[8]

        # 5. Register forward and backward hooks
        activations = []
        gradients = []

        def forward_hook(module, inp, out):
            activations.append(out)

        def backward_hook(module, grad_in, grad_out):
            gradients.append(grad_out[0])

        h_fwd = target_layer.register_forward_hook(forward_hook)
        h_bwd = target_layer.register_full_backward_hook(backward_hook)

        try:
            # 6. Forward pass
            logits = model(input_tensor)
            probabilities = torch.softmax(logits, dim=1)[0]
            pred_idx = int(torch.argmax(probabilities).item())
            pred_class = self.classes[pred_idx]
            confidence = float(probabilities[pred_idx].item())

            # Resolve target class index
            chosen_index = self.validate_target_class(target_class, target_index)
            if chosen_index is None:
                chosen_index = pred_idx

            chosen_class = self.classes[chosen_index]

            # 7. Backward pass for target class score
            model.zero_grad()
            score = logits[0, chosen_index]
            score.backward()

        except Exception as err:
            logger.error("Grad-CAM forward/backward pass failed: %s", err, exc_info=True)
            raise ModelInferenceError(f"Grad-CAM computation failed: {err}") from err
        finally:
            # Strictly clean up hooks and reset model gradients
            h_fwd.remove()
            h_bwd.remove()
            model.zero_grad()

        # 8. Compute Grad-CAM weights and activation maps
        if not activations or not gradients:
            raise ModelInferenceError("Grad-CAM hooks failed to capture activations or gradients.")

        act = activations[0]  # [1, 1792, H, W]
        grad = gradients[0]   # [1, 1792, H, W]

        # Global average pooling of gradients
        weights = torch.mean(grad, dim=(2, 3), keepdim=True)  # [1, 1792, 1, 1]

        # Weighted combination of feature maps
        cam = torch.sum(weights * act, dim=1, keepdim=True)    # [1, 1, H, W]

        # Apply ReLU to retain only positive contributions
        cam = F.relu(cam)
        cam_np = cam.squeeze().detach().cpu().numpy()          # [H, W]

        # Safe min-max normalization to [0.0, 1.0]
        cam_min, cam_max = float(cam_np.min()), float(cam_np.max())
        if cam_max > cam_min and not np.isnan(cam_max) and not np.isnan(cam_min):
            cam_norm = (cam_np - cam_min) / (cam_max - cam_min)
        else:
            logger.warning("Constant or zero Grad-CAM heatmap detected for class '%s'", chosen_class)
            cam_norm = np.zeros_like(cam_np, dtype=np.float32)

        # 9. Resize heatmap to match original image dimensions exactly
        cam_pil = Image.fromarray((cam_norm * 255.0).astype(np.uint8), mode="L")
        resized_cam_pil = cam_pil.resize((orig_w, orig_h), resample=Image.Resampling.BILINEAR)
        resized_cam = np.array(resized_cam_pil).astype(np.float32) / 255.0

        # 10. Apply Jet colormap and blend overlay
        heatmap_rgb = self.apply_jet_colormap(resized_cam)
        orig_arr = np.array(orig_image.convert("RGB"))
        alpha_clamped = min(max(alpha, 0.1), 0.9)
        overlay_arr = (alpha_clamped * heatmap_rgb + (1.0 - alpha_clamped) * orig_arr).astype(np.uint8)
        overlay_pil = Image.fromarray(overlay_arr)

        # 11. Encode to JPEG bytes and Base64 Data URI
        buf = io.BytesIO()
        overlay_pil.save(buf, format="JPEG", quality=90)
        jpeg_bytes = buf.getvalue()
        b64_uri = f"data:image/jpeg;base64,{base64.b64encode(jpeg_bytes).decode('utf-8')}"

        # 12. Save copy to safe static directory with unique filename
        filename = f"gradcam_{uuid.uuid4().hex[:12]}_{chosen_class}.jpg"
        file_path = config.GRADCAM_OUTPUT_DIR / filename
        try:
            overlay_pil.save(file_path, format="JPEG", quality=90)
            vis_url = f"/static/visualizations/gradcam/{filename}"
        except Exception as e:
            logger.warning("Could not persist Grad-CAM image to disk: %s", e)
            vis_url = None

        return {
            "status": "success",
            "predicted_class": pred_class,
            "predicted_index": pred_idx,
            "confidence": round(confidence, 4),
            "target_class": chosen_class,
            "target_index": chosen_index,
            "target_layer": self.target_layer_name,
            "image_dimensions": {"width": orig_w, "height": orig_h},
            "heatmap_intensity_mean": round(float(resized_cam.mean()), 4),
            "heatmap_intensity_max": round(float(resized_cam.max()), 4),
            "overlay_image": b64_uri,
            "visualization_url": vis_url,
            "raw_bytes": jpeg_bytes,
            "media_type": "image/jpeg",
            "device": self.device,
            "limitations_note": (
                "Grad-CAM is a visual explanation of neural network activation sensitivity, "
                "not proof of biological causation or definitive lesion pathology. "
                "Highlighted regions indicate receptive fields that increased the target class score, "
                "not verified histological boundaries."
            ),
        }


# Singleton accessor
gradcam_service = GradCAMService()
