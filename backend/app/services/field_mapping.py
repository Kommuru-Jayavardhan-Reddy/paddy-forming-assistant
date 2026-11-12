"""
Paddy Farming Assistant - Field Mapping Service (STEP 11D.1)
Encapsulates verified mapping between leaf images, field IDs,
and Sentinel-2 satellite time-series data.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from app import config
from app.exceptions import FieldNotFoundError, SatelliteDataUnavailableError, InvalidCoordinatesError


logger = logging.getLogger(__name__)


class FieldMappingService:
    """
    Manages and validates verified field mapping and satellite sequence artifacts.
    Provides fast, deterministic lookups from image or field ID to satellite time-series data.
    """

    _instance: Optional["FieldMappingService"] = None

    def __init__(self):
        self._sequences: Optional[np.ndarray] = None
        self._field_embeddings: Optional[np.ndarray] = None
        self._master_fields: Dict[str, Dict[str, Any]] = {}
        self._dataset_images: Dict[str, Dict[str, Any]] = {}
        self._field_dates: Dict[str, List[str]] = {}
        self._is_loaded = False
        self._load_errors: List[str] = []

    @classmethod
    def get_instance(cls) -> "FieldMappingService":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load()
        return cls._instance

    def load(self, reload: bool = False):
        """
        Loads all mapping artifacts into memory.
        """
        if self._is_loaded and not reload:
            return

        self._load_errors.clear()
        self._master_fields.clear()
        self._dataset_images.clear()
        self._field_dates.clear()


        # 1. Load Satellite Sequences Tensor (58, 10, 3)
        seq_path: Path = config.SATELLITE_SEQUENCES_PATH
        if seq_path.exists():
            try:
                self._sequences = np.load(seq_path, allow_pickle=False)
                if self._sequences.shape != (config.TOTAL_SATELLITE_FIELDS, config.SATELLITE_TIMESTEPS, config.NUM_SATELLITE_FEATURES):
                    err = f"Satellite sequence shape mismatch: expected ({config.TOTAL_SATELLITE_FIELDS}, {config.SATELLITE_TIMESTEPS}, {config.NUM_SATELLITE_FEATURES}), got {self._sequences.shape}"
                    self._load_errors.append(err)
                    logger.error(err)
            except Exception as e:
                err = f"Failed to load satellite sequences from {seq_path}: {e}"
                self._load_errors.append(err)
                logger.error(err)
        else:
            err = f"Satellite sequences file not found at: {seq_path}"
            self._load_errors.append(err)
            logger.error(err)

        # 2. Load Field Embeddings Tensor (58, 256) if available
        emb_path: Path = config.FIELD_EMBEDDINGS_PATH
        if emb_path.exists():
            try:
                self._field_embeddings = np.load(emb_path, allow_pickle=False)
            except Exception as e:
                logger.warning("Could not load field embeddings: %s", e)

        # 3. Load Master Field Catalog (58 fields)
        master_csv: Path = config.FIELD_MASTER_MAPPING_PATH
        if master_csv.exists():
            try:
                with open(master_csv, mode="r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        fid = row["field_id"]
                        self._master_fields[fid] = {
                            "field_id": fid,
                            "clean_field_id": row.get("clean_field_id", ""),
                            "latitude": float(row["latitude"]),
                            "longitude": float(row["longitude"]),
                            "sentinel2_image_count": int(row.get("sentinel2_image_count", 0)),
                            "embedding_index": int(row.get("embedding_index", -1)),
                            "sequence_index": int(row.get("sequence_index", -1)),
                        }
            except Exception as e:
                err = f"Failed to load master field catalog from {master_csv}: {e}"
                self._load_errors.append(err)
                logger.error(err)
        else:
            err = f"Master field catalog not found at: {master_csv}"
            self._load_errors.append(err)
            logger.error(err)

        # 4. Load Multimodal Dataset Images (640 records)
        dataset_csv: Path = config.MULTIMODAL_DATASET_MAPPING_PATH
        if dataset_csv.exists():
            try:
                with open(dataset_csv, mode="r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        img_name = row["image_name"]
                        self._dataset_images[img_name] = {
                            "image_name": img_name,
                            "image_embedding_index": int(row.get("image_embedding_index", -1)),
                            "latitude": float(row["latitude"]),
                            "longitude": float(row["longitude"]),
                            "status": row.get("status", ""),
                            "gps_field_id": row.get("gps_field_id", ""),
                            "nearest_satellite_field": row.get("nearest_satellite_field", ""),
                            "distance_km": float(row.get("distance_km", 0.0)),
                            "decision": row.get("decision", ""),
                            "satellite_embedding_index": int(row.get("satellite_embedding_index", -1)),
                            "disease_label": row.get("disease_label", ""),
                            "disease_class_index": int(row.get("disease_class_index", -1)),
                            "label_11class": int(row.get("label_11class", -1)),
                            "split": row.get("split", ""),
                        }
            except Exception as e:
                err = f"Failed to load dataset image mapping from {dataset_csv}: {e}"
                self._load_errors.append(err)
                logger.error(err)
        else:
            err = f"Dataset image mapping not found at: {dataset_csv}"
            self._load_errors.append(err)
            logger.error(err)

        # 5. Load Observation Dates from Sentinel-2 timeseries CSV if available
        timeseries_csv: Path = config.SENTINEL2_TIMESERIES_CSV_PATH
        if timeseries_csv.exists():
            try:
                with open(timeseries_csv, mode="r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        fid = row["field_id"]
                        date_val = row.get("date", "").strip()
                        if fid not in self._field_dates:
                            self._field_dates[fid] = []
                        if date_val:
                            self._field_dates[fid].append(date_val)
            except Exception as e:
                logger.warning("Could not load observation dates from %s: %s", timeseries_csv, e)

        self._is_loaded = len(self._load_errors) == 0

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def get_field(self, field_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves field metadata and satellite sequence by field ID.
        """
        if not self._is_loaded:
            self.load()

        fid = field_id.strip()
        if fid not in self._master_fields and fid.upper() in self._master_fields:
            fid = fid.upper()

        field = self._master_fields.get(fid)
        if not field:
            return None

        result = dict(field)
        seq_idx = field["sequence_index"]
        if self._sequences is not None and 0 <= seq_idx < len(self._sequences):
            result["sequence"] = self._sequences[seq_idx]
            result["sequence_shape"] = self._sequences[seq_idx].shape
            result["features"] = config.SATELLITE_FEATURES

        if self._field_embeddings is not None and 0 <= seq_idx < len(self._field_embeddings):
            result["embedding"] = self._field_embeddings[seq_idx]

        return result

    def get_field_coordinates(self, field_id: str) -> Tuple[float, float]:
        """
        Resolves authoritative centroid coordinates (latitude, longitude) for a given field ID.
        Raises FieldNotFoundError (HTTP 404) if field_id is unknown.
        Raises InvalidCoordinatesError (HTTP 400) if coordinates are missing, non-numeric,
        or outside valid geographic bounds [-90.0, 90.0], [-180.0, 180.0].
        """
        if not self._is_loaded:
            self.load()

        if not field_id or not isinstance(field_id, str):
            raise FieldNotFoundError(f"Invalid field identifier: '{field_id}'.")

        fid = field_id.strip()
        if fid not in self._master_fields and fid.upper() in self._master_fields:
            fid = fid.upper()

        if fid not in self._master_fields:
            logger.warning("Field coordinate resolution failed: field '%s' not found.", field_id)
            raise FieldNotFoundError(f"Field '{field_id}' was not found in the master field catalog.")

        field_info = self._master_fields[fid]
        lat = field_info.get("latitude")
        lon = field_info.get("longitude")

        if lat is None or lon is None:
            raise InvalidCoordinatesError(f"Field '{fid}' does not have coordinates defined in master catalog.")

        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (ValueError, TypeError):
            raise InvalidCoordinatesError(f"Field '{fid}' contains non-numeric coordinates: lat={lat}, lon={lon}.")

        import math
        if math.isnan(lat_f) or math.isinf(lat_f) or math.isnan(lon_f) or math.isinf(lon_f):
            raise InvalidCoordinatesError(f"Field '{fid}' contains NaN or Infinite coordinate values.")

        if not (-90.0 <= lat_f <= 90.0):
            raise InvalidCoordinatesError(f"Field '{fid}' latitude {lat_f} is out of valid range [-90.0, 90.0].")

        if not (-180.0 <= lon_f <= 180.0):
            raise InvalidCoordinatesError(f"Field '{fid}' longitude {lon_f} is out of valid range [-180.0, 180.0].")

        return lat_f, lon_f

    def get_satellite_sequence(self, field_id: str) -> Optional[np.ndarray]:
        """
        Returns raw satellite time-series array (10, 3) for the given field.
        """
        field_info = self.get_field(field_id)
        if field_info and "sequence" in field_info:
            return field_info["sequence"]
        return None

    def register_custom_field(
        self,
        field_id: str,
        latitude: float,
        longitude: float,
        field_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registers a user-created field in memory, linking to the nearest Sentinel-2
        observation grid cell to provide seamless satellite time-series analysis.
        """
        if not self._is_loaded:
            self.load()

        fid = field_id.strip()
        best_fid = "FIELD_01"
        min_dist = float("inf")
        for m_fid, m_info in self._master_fields.items():
            if m_info.get("sequence_index", -1) >= 0:
                m_lat = m_info["latitude"]
                m_lon = m_info["longitude"]
                dist = (latitude - m_lat) ** 2 + (longitude - m_lon) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_fid = m_fid

        closest = self._master_fields.get(best_fid, {})
        entry = {
            "field_id": fid,
            "clean_field_id": closest.get("clean_field_id", "CLEAN_FIELD_001"),
            "latitude": latitude,
            "longitude": longitude,
            "sentinel2_image_count": closest.get("sentinel2_image_count", 10),
            "embedding_index": closest.get("embedding_index", 0),
            "sequence_index": closest.get("sequence_index", 0),
            "field_name": field_name or fid,
            "is_user_created": True,
        }
        self._master_fields[fid] = entry
        if fid.upper() != fid:
            self._master_fields[fid.upper()] = entry
        return entry

    def get_field_timeseries_data(self, field_id: str) -> Dict[str, Any]:
        """
        Retrieves fully structured, verified satellite time-series data for the given field.
        Raises FieldNotFoundError (404) if field_id is unknown.
        Raises SatelliteDataUnavailableError (503) if sequence data is invalid or missing.
        """
        if not self._is_loaded:
            self.load()

        fid = field_id.strip()
        if fid not in self._master_fields and fid.upper() in self._master_fields:
            fid = fid.upper()

        if fid not in self._master_fields:
            logger.warning("Field not found: '%s'", field_id)
            raise FieldNotFoundError(f"Field '{field_id}' was not found in the master field catalog.")

        if self._sequences is None:
            logger.error("Satellite sequence tensor is unavailable.")
            raise SatelliteDataUnavailableError("Satellite time-series sequence data is not loaded.")

        field_info = self._master_fields[fid]

        seq_idx = field_info["sequence_index"]

        if not (0 <= seq_idx < len(self._sequences)):
            logger.error("Invalid sequence index %d for field %s", seq_idx, field_id)
            raise SatelliteDataUnavailableError(f"Sequence index {seq_idx} for field '{field_id}' is out of range.")

        raw_seq = self._sequences[seq_idx]

        if raw_seq.shape != (config.SATELLITE_TIMESTEPS, config.NUM_SATELLITE_FEATURES):
            logger.error("Malformed sequence shape %s for field %s", raw_seq.shape, field_id)
            raise SatelliteDataUnavailableError(f"Satellite sequence has malformed dimensions {raw_seq.shape}.")

        if np.isnan(raw_seq).any() or np.isinf(raw_seq).any():
            logger.error("Satellite sequence for field %s contains NaN or Inf values.", field_id)
            raise SatelliteDataUnavailableError(f"Satellite sequence for field '{field_id}' contains corrupt numerical values.")

        dates = self._field_dates.get(field_id)
        has_dates = bool(dates and len(dates) == config.SATELLITE_TIMESTEPS)

        timesteps = []
        for t in range(config.SATELLITE_TIMESTEPS):
            timesteps.append({
                "timestep": t + 1,
                "date": dates[t] if (dates and t < len(dates)) else None,
                "ndvi": float(raw_seq[t, 0]),
                "ndre": float(raw_seq[t, 1]),
                "gndvi": float(raw_seq[t, 2]),
            })

        return {
            "field_id": field_info["field_id"],
            "clean_field_id": field_info.get("clean_field_id"),
            "sequence_index": seq_idx,

            "features": config.SATELLITE_FEATURES,
            "total_timesteps": config.SATELLITE_TIMESTEPS,
            "coordinates": {
                "latitude": field_info["latitude"],
                "longitude": field_info["longitude"],
            },
            "has_dates": has_dates,
            "timesteps": timesteps,
        }


    def get_image_mapping(self, image_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves field mapping for a known dataset leaf image.
        """
        if not self._is_loaded:
            self.load()

        record = self._dataset_images.get(image_name)
        if not record:
            return None

        result = dict(record)
        sat_field = record["nearest_satellite_field"]
        field_info = self.get_field(sat_field)
        if field_info:
            result["field_metadata"] = field_info
            if "sequence" in field_info:
                result["sequence"] = field_info["sequence"]
        return result

    def list_fields(self) -> List[Dict[str, Any]]:
        """
        Returns list of all 58 master fields with their active dataset usage status.
        """
        if not self._is_loaded:
            self.load()

        active_fields = set(r["nearest_satellite_field"] for r in self._dataset_images.values())
        results = []
        for fid in sorted(self._master_fields.keys(), key=lambda x: int(x.split("_")[1])):
            item = dict(self._master_fields[fid])
            item["has_images"] = fid in active_fields
            results.append(item)
        return results

    def validate_mappings(self) -> Dict[str, Any]:
        """
        Executes strict verification of all field mapping relationships and data structures.
        """
        if not self._is_loaded:
            self.load()

        report: Dict[str, Any] = {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "checks": {},
        }

        if self._load_errors:
            report["status"] = "FAIL"
            report["errors"].extend(self._load_errors)
            return report

        # Check 1: Satellite sequences tensor
        if self._sequences is None:
            report["status"] = "FAIL"
            report["errors"].append("Satellite sequences tensor is None.")
        else:
            has_nan = bool(np.isnan(self._sequences).any())
            has_inf = bool(np.isinf(self._sequences).any())
            correct_shape = self._sequences.shape == (config.TOTAL_SATELLITE_FIELDS, config.SATELLITE_TIMESTEPS, config.NUM_SATELLITE_FEATURES)
            correct_dtype = str(self._sequences.dtype) == "float32"

            report["checks"]["sequences_shape"] = {
                "expected": (58, 10, 3),
                "actual": self._sequences.shape,
                "passed": correct_shape,
            }
            report["checks"]["sequences_numerics"] = {
                "has_nan": has_nan,
                "has_inf": has_inf,
                "dtype": str(self._sequences.dtype),
                "passed": not has_nan and not has_inf and correct_dtype,
            }
            if not correct_shape or has_nan or has_inf or not correct_dtype:
                report["status"] = "FAIL"
                report["errors"].append("Satellite sequence tensor validation failed.")

        # Check 2: Master field catalog
        master_count = len(self._master_fields)
        expected_master = config.TOTAL_SATELLITE_FIELDS
        report["checks"]["master_field_count"] = {
            "expected": expected_master,
            "actual": master_count,
            "passed": master_count == expected_master,
        }

        invalid_indices = []
        for fid, fmeta in self._master_fields.items():
            field_num = int(fid.split("_")[1])
            expected_idx = field_num - 1
            if fmeta["sequence_index"] != expected_idx or fmeta["embedding_index"] != expected_idx:
                invalid_indices.append((fid, fmeta["sequence_index"], expected_idx))

        report["checks"]["master_indexing"] = {
            "invalid_indices_count": len(invalid_indices),
            "passed": len(invalid_indices) == 0,
        }
        if master_count != expected_master or invalid_indices:
            report["status"] = "FAIL"
            report["errors"].append("Master field catalog indexing mismatch.")

        # Check 3: Dataset images mapping
        dataset_count = len(self._dataset_images)
        report["checks"]["dataset_image_count"] = {
            "expected": 640,
            "actual": dataset_count,
            "passed": dataset_count == 640,
        }

        unmapped_images = []
        mismatched_sat_indices = []
        unique_sat_fields = set()

        for img_name, record in self._dataset_images.items():
            sat_field = record["nearest_satellite_field"]
            sat_idx = record["satellite_embedding_index"]
            unique_sat_fields.add(sat_field)

            if sat_field not in self._master_fields:
                unmapped_images.append((img_name, sat_field, "Field not in master"))
            else:
                expected_idx = self._master_fields[sat_field]["sequence_index"]
                if sat_idx != expected_idx:
                    mismatched_sat_indices.append((img_name, sat_field, sat_idx, expected_idx))

        report["checks"]["dataset_alignment"] = {
            "unmapped_images": len(unmapped_images),
            "mismatched_indices": len(mismatched_sat_indices),
            "unique_satellite_fields_used": len(unique_sat_fields),
            "passed": len(unmapped_images) == 0 and len(mismatched_sat_indices) == 0,
        }

        if unmapped_images or mismatched_sat_indices or dataset_count != 640:
            report["status"] = "FAIL"
            report["errors"].append("Dataset image to field alignment validation failed.")

        # Check 4: Unused satellite fields note
        unused_fields = sorted(set(self._master_fields.keys()) - unique_sat_fields, key=lambda x: int(x.split("_")[1]))
        report["checks"]["unused_satellite_fields"] = {
            "count": len(unused_fields),
            "field_ids": unused_fields,
            "passed": len(unused_fields) == 22,
        }

        return report
