"""
PINN inference.

Loads a trained network, prepares input features for a (farm, crop)
pair, runs a forward pass, denormalizes outputs, and computes physics
residuals for auditing.
"""
from __future__ import annotations

import logging
import os

import torch

from apps.pinn_engine.ml.network import (
    load_network,
    load_network_from_db,
)
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


def compute_residuals(
    predictions: torch.Tensor,
    features: torch.Tensor,
    feature_names: list[str],
    output_names: list[str],
) -> dict[str, float]:
    fmap = feature_index_map(feature_names)
    omap = output_index_map(output_names)

    return {
        'water_balance':       float(water_balance_loss(predictions, features, fmap, omap).item()),
        'nutrient_cycle':      float(nutrient_cycle_loss(predictions, features, fmap, omap).item()),
        'energy_conservation': float(energy_conservation_loss(predictions, features, fmap, omap).item()),
    }


def compute_attributions(
    net,
    x_tensor: torch.Tensor,
    feature_names: list[str],
) -> dict[str, float]:
    x = x_tensor.clone().detach().requires_grad_(True)
    y = net(x).mean()
    y.backward()

    if x.grad is None:
        return {name: 0.0 for name in feature_names}

    grads = x.grad.detach().abs().mean(dim=0).cpu().numpy()
    return {name: float(grads[i]) for i, name in enumerate(feature_names)}


def _load_trained_network(pinn_model):
    """
    Load the trained network, preferring the DB-stored artifact
    (survives container restarts) and falling back to the file on
    disk (legacy path, wiped on Render when the service idles out).
    """
    # Preferred: DB JSON. Survives /tmp wipes on Render free tier.
    if pinn_model.artifact_json:
        try:
            return load_network_from_db(pinn_model)
        except Exception as e:
            logger.warning(
                "DB artifact load failed for PINNModel pk=%s (%s); "
                "falling back to file.",
                pinn_model.pk, e,
            )

    # Fallback: file on disk (legacy).
    if pinn_model.artifact_path:
        if os.path.exists(pinn_model.artifact_path):
            return load_network(pinn_model.artifact_path)
        logger.warning(
            "Artifact file '%s' does not exist for PINNModel pk=%s; "
            "file may have been wiped. Retrain or check DB artifact.",
            pinn_model.artifact_path, pinn_model.pk,
        )

    # Nothing to load
    raise ValueError(
        f"PINNModel '{pinn_model.name}' has no trained artifact. "
        f"Run a training job first."
    )


def run_inference(
    pinn_model,
    farm,
    crop,
    soil_test=None,
    weather_record=None,
) -> dict:
    feature_names = list(pinn_model.input_features or [])
    output_names  = list(pinn_model.output_targets or [])

    if not feature_names or not output_names:
        raise ValueError("PINNModel missing feature/output configuration.")

    # Raises ValueError with a user-friendly message if no artifact
    # is available in either the DB or on disk.
    net = _load_trained_network(pinn_model)
    net.eval()

    feats = extract_features(
        farm=farm, crop=crop,
        soil_test=soil_test, weather_record=weather_record,
    )
    x = to_tensor(feats, feature_names)

    with torch.no_grad():
        preds = net(x)

    raw = preds.squeeze(0).cpu().numpy()
    outputs = {
        name: denormalize(float(raw[i]), name)
        for i, name in enumerate(output_names)
    }

    try:
        attributions = compute_attributions(net, x, feature_names)
    except Exception as e:
        logger.warning("Attribution failed: %s", e)
        attributions = {}

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
