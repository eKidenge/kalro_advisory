"""
Feature extraction and normalization.

Converts Django model instances (farm, soil test, weather, crop)
into a normalized numeric vector the PINN can consume.

The order of features MUST match PINNModel.input_features exactly —
that's how we know which column means what.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

import numpy as np
import torch
from django.utils import timezone

logger = logging.getLogger(__name__)


# ==================================================================
# Range table — used for normalization
# ==================================================================
FEATURE_RANGES = {
    # Climate
    'rainfall':       (0.0,    200.0),    # mm (period)
    'temp_min':       (0.0,     30.0),    # °C
    'temp_max':       (10.0,    45.0),    # °C
    'humidity':       (0.0,    100.0),    # %
    'et':             (0.0,     15.0),    # mm/day

    # Soil
    'soil_ph':        (3.0,     10.0),
    'soil_n':         (0.0,      1.0),    # %
    'soil_p':         (0.0,    100.0),    # ppm
    'soil_k':         (0.0,    500.0),    # ppm
    'soil_oc':        (0.0,     10.0),    # organic carbon %
    'soil_cec':       (0.0,     50.0),    # meq/100g

    # Crop requirements
    'crop_water_req': (0.0,   2000.0),    # mm
    'crop_n_req':     (0.0,    300.0),    # kg/ha
    'crop_p_req':     (0.0,    150.0),
    'crop_k_req':     (0.0,    200.0),
    'base_temp':      (0.0,     30.0),    # °C
    'max_temp':       (20.0,    45.0),    # °C

    # Management
    'fertilizer_n':   (0.0,    200.0),    # kg/ha applied
    'fertilizer_p':   (0.0,    100.0),
    'fertilizer_k':   (0.0,    150.0),
    'altitude':       (0.0,   3000.0),    # m
}


def normalize(value: float, name: str) -> float:
    """Scale a raw value into [0, 1] using FEATURE_RANGES."""
    lo, hi = FEATURE_RANGES.get(name, (0.0, 1.0))
    if hi == lo:
        return 0.0
    v = (float(value) - lo) / (hi - lo)
    return max(0.0, min(1.0, v))


# ==================================================================
# Feature extraction from Django instances
# ==================================================================
def extract_features(
    farm,
    crop,
    soil_test=None,
    weather_record=None,
    forecast=None,
) -> dict[str, float]:
    """
    Build a feature dict for a single (farm, crop) pair.

    Args are Django model instances. soil_test and weather_record are
    optional — if None, we fall back to sensible defaults.
    """
    feats: dict[str, float] = {}

    # ---- Climate ----
    if weather_record:
        feats['rainfall']  = float(weather_record.rainfall_mm or 0.0)
        feats['temp_min']  = float(weather_record.temp_min_c or 15.0)
        feats['temp_max']  = float(weather_record.temp_max_c or 28.0)
        feats['humidity']  = float(weather_record.humidity_pct or 60.0)
        feats['et']        = float(weather_record.evapotranspiration_mm or 4.0)
    else:
        feats['rainfall']  = 50.0
        feats['temp_min']  = 15.0
        feats['temp_max']  = 28.0
        feats['humidity']  = 60.0
        feats['et']        = 4.0

    # ---- Soil ----
    if soil_test:
        feats['soil_ph'] = float(soil_test.ph or 6.5)
        feats['soil_n']  = float(soil_test.nitrogen_pct or 0.15)
        feats['soil_p']  = float(soil_test.phosphorus_ppm or 20.0)
        feats['soil_k']  = float(soil_test.potassium_ppm or 150.0)
        feats['soil_oc'] = float(soil_test.organic_carbon_pct or 1.5)
        feats['soil_cec'] = float(soil_test.cec_meq or 15.0)
    else:
        feats['soil_ph'] = 6.5
        feats['soil_n']  = 0.15
        feats['soil_p']  = 20.0
        feats['soil_k']  = 150.0
        feats['soil_oc'] = 1.5
        feats['soil_cec'] = 15.0

    # ---- Crop ----
    feats['crop_water_req'] = float(getattr(crop, 'water_requirement_mm', 500) or 500)
    feats['crop_n_req']     = float(getattr(crop, 'n_requirement_kg_ha', 80) or 80)
    feats['crop_p_req']     = float(getattr(crop, 'p_requirement_kg_ha', 40) or 40)
    feats['crop_k_req']     = float(getattr(crop, 'k_requirement_kg_ha', 40) or 40)
    feats['base_temp']      = float(getattr(crop, 'base_temp_c', 10) or 10)
    feats['max_temp']       = float(getattr(crop, 'max_temp_c', 35) or 35)

    # ---- Management (defaults — overridden by caller if known) ----
    feats['fertilizer_n'] = 0.0
    feats['fertilizer_p'] = 0.0
    feats['fertilizer_k'] = 0.0

    # ---- Farm ----
    feats['altitude'] = float(getattr(farm, 'altitude_m', 0) or 0)

    return feats


# ==================================================================
# Vectorization
# ==================================================================
def to_vector(
    feature_dict: dict[str, float],
    feature_names: list[str],
) -> np.ndarray:
    """
    Reorder + normalize the feature dict into a numpy vector matching
    feature_names. Missing features become 0.0.
    """
    vec = np.zeros(len(feature_names), dtype=np.float32)
    for i, name in enumerate(feature_names):
        raw = feature_dict.get(name, 0.0)
        vec[i] = normalize(raw, name)
    return vec


def to_tensor(
    feature_dict: dict[str, float],
    feature_names: list[str],
) -> torch.Tensor:
    """Return a (1, n_inputs) tensor ready for a forward pass."""
    return torch.from_numpy(to_vector(feature_dict, feature_names)).unsqueeze(0)


def feature_index_map(feature_names: list[str]) -> dict[str, int]:
    """Return {'rainfall': 0, 'soil_n': 3, ...}."""
    return {name: i for i, name in enumerate(feature_names)}


def output_index_map(output_names: list[str]) -> dict[str, int]:
    return {name: i for i, name in enumerate(output_names)}


# ==================================================================
# Denormalization for outputs
# ==================================================================
OUTPUT_RANGES = {
    'yield_kg_ha':    (0.0,   12000.0),
    'yield':          (0.0,   12000.0),
    'n_uptake':       (0.0,     300.0),
    'p_uptake':       (0.0,     150.0),
    'k_uptake':       (0.0,     200.0),
    'water_stress':   (0.0,       1.0),
    'water_use_mm':   (0.0,    2000.0),
    'nue':            (0.0,       1.0),
}


def denormalize(value: float, name: str) -> float:
    """Inverse of `normalize` for output variables."""
    lo, hi = OUTPUT_RANGES.get(name, (0.0, 1.0))
    return lo + float(value) * (hi - lo)
