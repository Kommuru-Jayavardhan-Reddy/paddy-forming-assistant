"""
Paddy Farming Assistant - OCR & EXIF GPS Extraction Service
Two-stage geographic coordinate extraction from uploaded field photos:
1. EXIF Metadata Extraction (Primary)
2. Computer Vision / Pillow + Tesseract OCR Extraction (Fallback for GPS Map Camera overlays)
"""

import io
import os
import re
import shutil
import tempfile
import subprocess
import logging
from typing import Dict, Any, Optional, Tuple

from PIL import Image, ExifTags, ImageOps

logger = logging.getLogger(__name__)

# Locate Tesseract OCR binary executable
TESSERACT_EXE = None
possible_paths = [
    shutil.which("tesseract"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\jayav\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]
for p in possible_paths:
    if p and os.path.exists(p):
        TESSERACT_EXE = p
        break


class OcrGpsService:
    """
    Extracts GPS coordinates (Latitude, Longitude) and textual location metadata
    from digital photos using EXIF inspection and OCR for GPS Map Camera overlays.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> "OcrGpsService":
        if cls._instance is None:
            cls._instance = OcrGpsService()
        return cls._instance

    def extract_gps(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Executes two-stage extraction:
        Stage 1: EXIF Metadata (Primary)
        Stage 2: OCR on visual text overlays (Fallback)
        """
        if not image_bytes:
            return self._empty_result("Empty image bytes received")

        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.warning(f"Could not open image for GPS extraction: {e}")
            return self._empty_result(f"Invalid image format: {e}")

        # Stage 1: EXIF GPS Extraction (Primary)
        exif_result = self._extract_exif_gps(image)
        if exif_result.get("found"):
            logger.info("GPS coordinates successfully extracted from EXIF metadata.")
            return exif_result

        # Stage 2: OCR GPS Extraction (Fallback)
        ocr_result = self._extract_ocr_gps(image)
        if ocr_result.get("found"):
            logger.info("GPS coordinates successfully extracted from image text via OCR.")
            return ocr_result

        return self._empty_result("No GPS coordinates detected in EXIF metadata or image text overlays.")

    def _extract_exif_gps(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extracts GPSLatitude and GPSLongitude from standard EXIF metadata.
        """
        try:
            exif = image.getexif()
            if not exif:
                return {"found": False}

            gps_ifd = None
            if hasattr(exif, "get_ifd"):
                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
            elif 34853 in exif:
                gps_ifd = exif[34853]

            if not gps_ifd:
                return {"found": False}

            # Tags: 1=LatRef, 2=Lat, 3=LonRef, 4=Lon
            lat_vals = gps_ifd.get(2) or gps_ifd.get(ExifTags.Base.GPSLatitude if hasattr(ExifTags, 'Base') else None)
            lon_vals = gps_ifd.get(4) or gps_ifd.get(ExifTags.Base.GPSLongitude if hasattr(ExifTags, 'Base') else None)
            lat_ref = str(gps_ifd.get(1, "N")).upper()
            lon_ref = str(gps_ifd.get(3, "E")).upper()

            if lat_vals and lon_vals and len(lat_vals) >= 3 and len(lon_vals) >= 3:
                def to_decimal(vals):
                    d = float(vals[0])
                    m = float(vals[1])
                    s = float(vals[2])
                    return d + (m / 60.0) + (s / 3600.0)

                lat = to_decimal(lat_vals)
                lon = to_decimal(lon_vals)

                if lat_ref == "S":
                    lat = -abs(lat)
                if lon_ref == "W":
                    lon = -abs(lon)

                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0 and not (lat == 0.0 and lon == 0.0):
                    return {
                        "found": True,
                        "latitude": round(lat, 6),
                        "longitude": round(lon, 6),
                        "latitude_ref": lat_ref if lat_ref in ["N", "S"] else ("N" if lat >= 0 else "S"),
                        "longitude_ref": lon_ref if lon_ref in ["E", "W"] else ("E" if lon >= 0 else "W"),
                        "source": "EXIF Metadata",
                        "status": "Successful",
                        "location_name": None,
                        "village": None,
                        "date_time": None,
                    }
        except Exception as e:
            logger.debug(f"EXIF parsing error: {e}")

        return {"found": False}

    def _extract_ocr_gps(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extracts GPS coordinates and location details printed directly on the image
        by GPS Map Camera, Solocator, or timestamp camera apps.
        """
        if not TESSERACT_EXE:
            logger.warning("Tesseract binary not found on system; skipping OCR stage.")
            return {"found": False}

        w, h = image.size

        # High-priority regions:
        # GPS Map Camera places the overlay banner at the bottom (y: 60% to 100%),
        # with the Google map thumbnail on the left (x: 0 to 20%) and textual details on the right (x: 20% to 100%).
        bottom_crop = image.crop((0, int(h * 0.60), w, h))
        bw, bh = bottom_crop.size
        bottom_text_area = bottom_crop.crop((int(bw * 0.20), 0, bw, bh))

        candidate_crops = [
            ("bottom_text_area", bottom_text_area),
            ("bottom_full", bottom_crop),
            ("top_banner", image.crop((0, 0, w, int(h * 0.35)))),
            ("full_image", image),
        ]

        for name, crop_img in candidate_crops:
            try:
                # 1. Grayscale & 2x enlargement for sharp character definitions
                gray = crop_img.convert("L")
                scaled = gray.resize((crop_img.width * 2, crop_img.height * 2), Image.Resampling.BICUBIC)

                # 2. Binary thresholding for bright text on dark banner
                thresh = scaled.point(lambda p: 255 if p > 175 else 0)

                for proc in [thresh, scaled]:
                    text = self._run_tesseract(proc)
                    parsed = self._parse_gps_text(text)
                    if parsed.get("found"):
                        parsed["source"] = "Image Text (OCR)"
                        parsed["status"] = "Successful"
                        return parsed
            except Exception as e:
                logger.debug(f"Preprocessing error on {name}: {e}")

        return {"found": False}

    def _run_tesseract(self, image: Image.Image) -> str:
        """
        Executes Tesseract binary via subprocess.
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                image.save(tmp.name, format="PNG")
                tmp_path = tmp.name

            proc = subprocess.run(
                [TESSERACT_EXE, tmp_path, "stdout", "--oem", "1", "-l", "eng"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                return proc.stdout or ""
        except Exception as e:
            logger.debug(f"Tesseract execution error: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        return ""

    def _parse_gps_text(self, text: str) -> Dict[str, Any]:
        """
        Parses OCR text for decimal or DMS coordinates and associated location metadata.
        """
        if not text or len(text.strip()) < 5:
            return {"found": False}

        # Normalize noisy unicode / degree artifacts
        clean = (
            text.replace("\xa0", " ")
            .replace("\ufffd", " ")
            .replace("*", " ")
            .replace("°", " ")
            .replace("º", " ")
        )

        lat: Optional[float] = None
        lon: Optional[float] = None
        lat_ref = "N"
        lon_ref = "E"

        # Regex Pattern 1: Explicit Lat ... Long ... labels
        lat_match = re.search(
            r"(?:lat(?:itude)?|l[\s.]*at)[\s.:=]*\s*([+-]?\d{1,2}(?:\.\d+)?)\s*(?:deg(?:rees)?)?\s*([NS])?",
            clean,
            re.IGNORECASE,
        )
        lon_match = re.search(
            r"(?:long(?:itude)?|l[\s.]*on|lng)[\s.:=]*\s*([+-]?\d{1,3}(?:\.\d+)?)\s*(?:deg(?:rees)?)?\s*([EW])?",
            clean,
            re.IGNORECASE,
        )

        if lat_match and lon_match:
            lat = float(lat_match.group(1))
            if lat_match.group(2):
                lat_ref = lat_match.group(2).upper()
            if lat_ref == "S":
                lat = -abs(lat)

            lon = float(lon_match.group(1))
            if lon_match.group(2):
                lon_ref = lon_match.group(2).upper()
            if lon_ref == "W":
                lon = -abs(lon)
        else:
            # Regex Pattern 2: Consecutive decimal coordinates with N/S, E/W indicators
            pair = re.search(
                r"([+-]?\d{1,2}\.\d{4,8})\s*([NS])?[\s,;|\n/]+([+-]?\d{1,3}\.\d{4,8})\s*([EW])?",
                clean,
                re.IGNORECASE,
            )
            if pair:
                lat = float(pair.group(1))
                if pair.group(2):
                    lat_ref = pair.group(2).upper()
                if lat_ref == "S":
                    lat = -abs(lat)

                lon = float(pair.group(3))
                if pair.group(4):
                    lon_ref = pair.group(4).upper()
                if lon_ref == "W":
                    lon = -abs(lon)

        # Coordinate Validation: -90 <= Lat <= +90, -180 <= Lon <= +180
        if lat is not None and lon is not None:
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0 and not (lat == 0.0 and lon == 0.0):
                location_name, village, date_time = self._extract_text_metadata(text)

                return {
                    "found": True,
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "latitude_ref": lat_ref if lat_ref in ["N", "S"] else ("N" if lat >= 0 else "S"),
                    "longitude_ref": lon_ref if lon_ref in ["E", "W"] else ("E" if lon >= 0 else "W"),
                    "location_name": location_name,
                    "village": village,
                    "date_time": date_time,
                }

        return {"found": False}

    def _extract_text_metadata(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extracts location name, village, and acquisition date/time from the OCR text block.
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        location_name = None
        village = None
        date_time = None

        for l in lines:
            lower = l.lower()
            # Date/Time
            if re.search(
                r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                lower,
            ):
                date_time = l.strip()
            # Village
            elif "village" in lower:
                vm = re.search(r"([A-Za-z0-9\s]+Village)", l, re.IGNORECASE)
                raw_village = vm.group(1).strip() if vm else l.strip()
                # Clean OCR artifact where 'i' before Village is read as 't' (e.g., Jangalapallt -> Jangalapalli)
                village = re.sub(r"([A-Za-z]+ll)t(\s+Village)", r"\1i\2", raw_village, flags=re.IGNORECASE)
            # Location Name (State/Country indicators, not coordinate line)
            elif (
                ("india" in lower or "pradesh" in lower or "district" in lower or "mandal" in lower)
                and not location_name
                and "lat" not in lower
                and "long" not in lower
            ):
                cleaned = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", l).strip()
                cleaned = re.sub(r"\s+[^\w\s]+$", "", cleaned).strip()
                if len(cleaned) > 3:
                    location_name = cleaned

        return location_name, village, date_time

    def _empty_result(self, message: str) -> Dict[str, Any]:
        return {
            "found": False,
            "latitude": None,
            "longitude": None,
            "latitude_ref": None,
            "longitude_ref": None,
            "source": "None",
            "status": "Not Found",
            "location_name": None,
            "village": None,
            "date_time": None,
            "message": message,
        }


ocr_gps_service = OcrGpsService.get_instance()
