"""
PINN inference.

Loads a trained network from disk, prepares input features for a
(farm, crop) pair, runs a forward pass, denormalizes the outputs,
and computes physics residuals for auditing.
"""
from __future__ import annotations

import logging
from typing import Optional

import torch

from apps.pinn_engine.ml.network import load_network
from apps.pinn_engine.ml.features import (
    extract_features,
    to_tensor,
    feature_index_map,
    output_index_map,
    denormalize,
)
from apps.pinn_engine.ml.physics import (
    water_balance_loss,
    nutrient_cycle_loss,
    energy_conservation_loss,
)

logger = logging.getLogger(__name__)


# ==================================================================
# Physics residual computation (for auditing)
# ==================================================================
def compute_residuals(
    predictions: torch.Tensor,
    features: torch.Tensor,
    feature_names: list[str],
    output_names: list[str],
) -> dict[str, float]:
    """
    Return per-constraint residuals for this prediction.
    Values close to 0 mean the prediction is physically consistent.
    """
    fmap = feature_index_map(feature_names)
    omap = output_index_map(output_names)

    return {
        'water_balance':      float(water_balance_loss(predictions, features, fmap, omap).item()),
        'nutrient_cycle':     float(nutrient_cycle_loss(predictions, features, fmap, omap).item()),
        'energy_conservation': float(energy_conservation_loss(predictions, features, fmap, omap).item()),
    }


# ==================================================================
# Feature attribution (simple gradient method)
# ==================================================================
def compute_attributions(
    net,
    x_tensor: torch.Tensor,
    feature_names: list[str],
) -> dict[str, float]:
    """
    Gradient-based feature attribution: |∂output / ∂input| per input.

    Uses a gradient of the mean output with respect to each input.
    Cheap and explainable enough for v1.
    """
    x = x_tensor.clone().detach().requires_grad_(True)
    y = net(x).mean()
    y.backward()

    if x.grad is None:
        return {name: 0.0 for name in feature_names}

    grads = x.grad.detach().abs().mean(dim=0).cpu().numpy()
    return {name: float(grads[i]) for i, name in enumerate(feature_names)}


# ==================================================================
# Main inference entry point
# ==================================================================
def run_inference(
    pinn_model,
    farm,
    crop,
    soil_test=None,
    weather_record=None,
) -> dict:
    """
    Run the model for one (farm, crop) pair.

    Returns:
        {
            'outputs': {name: value, ...},
            'attributions': {feature: weight, ...},
            'residuals': {constraint: value, ...},
        }
    """
    if not pinn_model.artifact_path:
        raise ValueError(
            f"PINNModel '{pinn_model.name}' has no trained artifact. "
            f"Run a training job first."
        )

    feature_names = list(pinn_model.input_features or [])
    output_names  = list(pinn_model.output_targets or [])

    if not feature_names or not output_names:
        raise ValueError("PINNModel missing feature/output configuration.")

    # ---- 1. Load network ----
    net = load_network(pinn_model.artifact_path)
    net.eval()

    # ---- 2. Extract + vectorize features ----
    feats = extract_features(
        farm=farm, crop=crop,
        soil_test=soil_test, weather_record=weather_record,
    )
    x = to_tensor(feats, feature_names)

    # ---- 3. Forward pass ----
    with torch.no_grad():
        preds = net(x)

    # ---- 4. Denormalize ----
    raw = preds.squeeze(0).cpu().numpy()
    outputs = {
        name: denormalize(float(raw[i]), name)
        for i, name in enumerate(output_names)
    }

    # ---- 5. Attributions ----
    try:
        attributions = compute_attributions(net, x, feature_names)
    except Exception as e:
        logger.warning("Attribution failed: %s", e)
        attributions = {}

    # ---- 6. Physics residuals ----
    try:
        residuals = compute_residuals(preds, x, feature_names, output_names)
    except Exception as e:
        logger.warning("Residual computation failed: %s", e)
        residuals = {}

    return {
        'outputs': outputs,
        'attributions': attributions,
        'residuals': residuals,
    }
